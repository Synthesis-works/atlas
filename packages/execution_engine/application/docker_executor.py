import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

# Network modes an untrusted benchmark container may use. "host" and
# "container:*" are explicitly forbidden: they would share the runner's
# network namespace (loopback services, metadata endpoints) with untrusted code.
_ALLOWED_NETWORK_MODES = ("none", "bridge")
_NAMED_NETWORK_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")

logger = logging.getLogger(__name__)


def _validate_network_mode(mode: str) -> str:
    if mode in _ALLOWED_NETWORK_MODES:
        return mode
    if mode.startswith("host") or mode.startswith("container:") or mode.startswith("none:"):
        raise ValueError(
            f"ATLAS_BENCHMARK_NETWORK={mode!r} is forbidden for untrusted benchmark "
            "containers. Allowed: 'none', 'bridge', or a named user-defined network."
        )
    if _NAMED_NETWORK_RE.match(mode):
        return mode
    raise ValueError(f"Invalid network mode {mode!r} for benchmark container.")


if TYPE_CHECKING:
    import docker
    from docker.errors import DockerException, ImageNotFound, NotFound
    from docker.types import Ulimit

try:
    import docker
    from docker.errors import DockerException, ImageNotFound, NotFound
    from docker.types import Ulimit
except ImportError:
    docker = None  # type: ignore
    DockerException = Exception  # type: ignore
    ImageNotFound = Exception  # type: ignore
    NotFound = Exception  # type: ignore
    Ulimit = object  # type: ignore

from packages.execution_engine.application.executor import (
    ExecutionContext,
    ExecutionProvenance,
    ExecutionResult,
    Executor,
    ExecutorError,
    ExecutorTimeout,
    ExecutorUnavailable,
)


class DockerExecutor(Executor):
    """Production executor that runs each benchmark attempt in an isolated Docker container.

    Security properties:
    - Runs as non-root user
    - Read-only root filesystem where possible
    - Dropped Linux capabilities
    - no-new-privileges
    - CPU, memory, PID limits enforced
    - Hard timeout enforced
    - Ephemeral container (auto-removed)
    - No Docker socket access
    - No host filesystem access
    - No database credentials
    - Controlled network access
    """

    # Default resource limits (can be overridden via execution_config)
    DEFAULT_CPU_LIMIT = 2.0  # CPU cores
    DEFAULT_MEMORY_LIMIT = "2g"  # Memory limit
    DEFAULT_PIDS_LIMIT = 100  # Process limit
    DEFAULT_TIMEOUT_SECONDS = 1800  # 30 minutes
    DEFAULT_IMAGE = "atlas/benchmark-runner:latest"
    DEFAULT_NETWORK_MODE = "none"

    # Only these provider credentials may ever reach the benchmark container.
    # Everything else in the runner environment (DB URLs, JWT, billing keys,
    # docker socket) is structurally excluded.
    PROVIDER_KEY_ALLOWLIST = (
        "GEMINI_API_KEY",
        "XAI_API_KEY",
        "MISTRAL_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    )

    def __init__(
        self,
        image: str | None = None,
        cpu_limit: float | None = None,
        memory_limit: str | None = None,
        pids_limit: int | None = None,
        timeout_seconds: int | None = None,
        network_mode: str | None = None,  # None -> ATLAS_BENCHMARK_NETWORK env -> "none"
        command: list[str] | None = None,
    ):
        self._image = image or os.environ.get("ATLAS_BENCHMARK_IMAGE", self.DEFAULT_IMAGE)
        self._cpu_limit = cpu_limit or self.DEFAULT_CPU_LIMIT
        self._memory_limit = memory_limit or self.DEFAULT_MEMORY_LIMIT
        self._pids_limit = pids_limit or self.DEFAULT_PIDS_LIMIT
        self._timeout_seconds = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS
        self._network_mode = _validate_network_mode(
            network_mode
            or os.environ.get("ATLAS_BENCHMARK_NETWORK", "").strip()
            or self.DEFAULT_NETWORK_MODE
        )
        self._command = command or ["python", "-m", "packages.execution_engine.container_entry"]
        self._client: Any = None  # type: ignore[assignment]

    @property
    def executor_type(self) -> str:
        return "docker"

    async def is_available(self) -> bool:
        try:
            client = self._get_client()
            client.ping()
            # Verify the image exists locally or can be pulled
            try:
                client.images.get(self._image)
            except ImageNotFound:
                # Try to pull
                try:
                    client.images.pull(self._image)
                except DockerException:
                    return False
            return True
        except Exception:
            return False

    def _get_client(self):  # type: ignore[return]
        if self._client is None:
            self._client = docker.from_env()  # type: ignore[attr-defined]
        return self._client

    def _provider_env(self) -> dict[str, str]:
        """Return only allow-listed provider keys present in the runner environment."""
        return {
            name: value for name in self.PROVIDER_KEY_ALLOWLIST if (value := os.environ.get(name))
        }

    def _build_container_config(self, context: ExecutionContext) -> dict[str, Any]:
        """Build the Docker container configuration with security hardening."""
        # Prepare the execution payload as JSON
        payload = {
            "execution_id": str(context.execution_id),
            "attempt_id": str(context.attempt_id),
            "attempt_number": context.attempt_number,
            "target_model": context.target_model,
            "benchmark_version_id": str(context.benchmark_version_id),
            "dataset_version_id": str(context.dataset_version_id)
            if context.dataset_version_id
            else None,
            "test_cases": context.test_cases,
            "execution_config": context.execution_config,
            "correlation_id": context.correlation_id,
            "trace_id": context.trace_id,
            "worker_id": context.worker_id,
        }

        # Environment variables for the container
        env = {
            "ATLAS_EXECUTION_PAYLOAD": json.dumps(payload),
            "ATLAS_EXECUTION_ID": str(context.execution_id),
            "ATLAS_ATTEMPT_ID": str(context.attempt_id),
            "ATLAS_TARGET_MODEL": context.target_model,
        }
        # Inject ONLY allow-listed provider keys sourced from the runner env at
        # launch time. Never DB credentials, JWT, billing keys, or the socket.
        env.update(self._provider_env())

        # Security-hardened host config
        host_config = self._get_client().api.create_host_config(
            # Resource limits
            cpu_quota=int(self._cpu_limit * 100000),
            cpu_period=100000,
            mem_limit=self._memory_limit,
            memswap_limit=self._memory_limit,  # Disable swap
            pids_limit=self._pids_limit,
            # Security
            read_only=True,
            security_opt=["no-new-privileges:true"],
            cap_drop=["ALL"],
            # Network
            network_mode=self._network_mode,
            # Do NOT auto-remove - we need to get logs first
            auto_remove=False,
            # Tmpfs for writable directories
            tmpfs={
                "/tmp": "rw,noexec,nosuid,size=100m",
                "/workspace": "rw,noexec,nosuid,size=500m",
            },
            # Ulimits
            ulimits=[
                docker.types.Ulimit(name="nofile", soft=1024, hard=1024),
                docker.types.Ulimit(name="nproc", soft=self._pids_limit, hard=self._pids_limit),
            ],
        )

        return {
            "image": self._image,
            "command": self._command,
            "environment": env,
            "host_config": host_config,
            "working_dir": "/workspace",
            "labels": {"atlas.benchmark": "true"},
            "detach": True,
        }

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        if not await self.is_available():
            raise ExecutorUnavailable(
                f"Docker runtime unavailable: cannot connect to Docker daemon or "
                f"image '{self._image}' not available"
            )

        client = self._get_client()
        created_at = datetime.now(UTC)
        provenance = ExecutionProvenance(
            executor_type=self.executor_type,
            image_ref=self._image,
            created_at=created_at,
            trace_id=context.trace_id,
            correlation_id=context.correlation_id,
            worker_id=context.worker_id,
        )
        # Record the exact image identity so an attempt row is reproducible
        # even if the tag is later re-pushed. Best-effort: a missing digest
        # must never block execution.
        try:
            provenance.image_digest = client.api.inspect_image(self._image)["Id"]
        except Exception:  # noqa: BLE001 - provenance enrichment only
            logger.warning("could not resolve image digest for %s", self._image)

        container = None
        try:
            # Create container
            config = self._build_container_config(context)
            container = client.api.create_container(**config)
            container_id = container["Id"]
            provenance.container_id = container_id[:12]

            # Start container
            client.api.start(container_id)
            provenance.started_at = datetime.now(UTC)

            # Wait for completion with timeout. A client-side wait timeout does
            # NOT stop the container, so we stop it explicitly and classify.
            try:
                exit_code = client.api.wait(container_id, timeout=self._timeout_seconds + 60)
            except Exception as wait_err:
                provenance.finished_at = datetime.now(UTC)
                is_timeout = (
                    type(wait_err).__name__ in ("ReadTimeout", "ConnectTimeout", "Timeout")
                    or "timed out" in str(wait_err).lower()
                    or "timeout" in str(wait_err).lower()
                )
                if is_timeout:
                    try:
                        client.api.stop(container_id, timeout=10)
                    except Exception:
                        pass  # force-removed in finally regardless
                    provenance.exit_code = 137
                    provenance.termination_reason = "timeout"
                    provenance.timed_out = True
                    timeout_exc = ExecutorTimeout(
                        f"Execution timed out after {self._timeout_seconds}s"
                    )
                    timeout_exc.provenance = provenance  # type: ignore[attr-defined]
                    raise timeout_exc from wait_err
                raise

            provenance.exit_code = exit_code.get("StatusCode", -1)
            provenance.finished_at = datetime.now(UTC)

            # Collect logs
            logs = client.api.logs(container_id, stdout=True, stderr=True, stream=False)
            logs_str = (
                logs.decode("utf-8", errors="replace") if isinstance(logs, bytes) else str(logs)
            )

            # Collect resource stats
            await self._collect_stats(client, container_id, provenance)

            # Determine termination reason
            if provenance.exit_code == 0:
                provenance.termination_reason = "completed"
            elif provenance.exit_code == 137:  # SIGKILL (OOM or timeout)
                if provenance.oom_killed:
                    provenance.termination_reason = "oom"
                else:
                    provenance.termination_reason = "timeout"
                    provenance.timed_out = True
            elif provenance.exit_code == 124 or "timeout" in logs_str.lower():
                provenance.termination_reason = "timeout"
                provenance.timed_out = True
            else:
                provenance.termination_reason = "error"

            # Parse results from container output
            outputs_data = self._parse_outputs(logs_str, context)

            return ExecutionResult(
                provenance=provenance,
                model_outputs=outputs_data,
                error_message=None
                if provenance.termination_reason == "completed"
                else logs_str[:5000],
            )

        except docker.errors.APIError as e:
            e.provenance = provenance  # type: ignore[attr-defined]
            if "timeout" in str(e).lower():
                provenance.termination_reason = "timeout"
                provenance.timed_out = True
                raise ExecutorTimeout(f"Execution timed out after {self._timeout_seconds}s") from e
            raise ExecutorError(f"Docker API error: {e}") from e

        except Exception as e:
            provenance.finished_at = datetime.now(UTC)
            provenance.termination_reason = "error"
            e.provenance = provenance  # type: ignore[attr-defined]
            raise ExecutorError(f"Docker execution failed: {e}") from e

        finally:
            # Ensure container cleanup
            if container:
                try:
                    client.api.remove_container(container["Id"], force=True, v=True)
                except Exception:
                    pass  # Best effort cleanup

    async def _collect_stats(
        self, client, container_id: str, provenance: ExecutionProvenance
    ) -> None:  # type: ignore[valid-type]
        """Collect resource usage statistics from the container."""
        try:
            stats = client.api.stats(container_id, stream=False, decode=True)

            # CPU usage: total_usage is cumulative CPU time in nanoseconds,
            # so a single post-exit sample yields true consumed CPU seconds.
            cpu_stats = stats.get("cpu_stats", {})
            total_usage_ns = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            if total_usage_ns:
                provenance.cpu_seconds = total_usage_ns / 1_000_000_000.0

            # Memory usage
            memory_stats = stats.get("memory_stats", {})
            if memory_stats:
                provenance.peak_memory_bytes = memory_stats.get("max_usage", 0) or memory_stats.get(
                    "usage", 0
                )

            # PIDs
            pids_stats = stats.get("pids_stats", {})
            if pids_stats:
                provenance.pids_peak = pids_stats.get("current", 0)

            # Network
            networks = stats.get("networks", {})
            if networks:
                rx = sum(n.get("rx_bytes", 0) for n in networks.values())
                tx = sum(n.get("tx_bytes", 0) for n in networks.values())
                provenance.network_rx_bytes = rx
                provenance.network_tx_bytes = tx

            # OOM check
            provenance.oom_killed = stats.get("oom_killed", False)

        except Exception:
            # Stats collection is best-effort
            pass

    def _parse_outputs(self, logs: str, context: ExecutionContext) -> list[dict]:
        """Parse model outputs from container stdout.

        The container entry point should output JSON lines with model outputs.
        Expected format per line: {"test_case_id": "...", "output": "...", "latency_ms": 123, "tokens": 45}
        """
        outputs = []
        for line in logs.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if "test_case_id" in data and "output" in data:
                    outputs.append(
                        {
                            "execution_id": str(context.execution_id),
                            "test_case_id": data["test_case_id"],
                            "raw_output": data["output"],
                            "duration_ms": data.get("latency_ms"),
                            "tokens_used": data.get("tokens"),
                        }
                    )
            except json.JSONDecodeError:
                # Not a JSON output line, skip
                continue
        return outputs
