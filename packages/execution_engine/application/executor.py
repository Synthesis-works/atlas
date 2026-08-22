import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class ExecutionProvenance:
    """Runtime provenance recorded for each execution attempt."""

    executor_type: str  # "local", "docker", "kubernetes", "aws_batch"
    container_id: str | None = None
    image_ref: str | None = None
    image_digest: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    termination_reason: str | None = None  # completed, timeout, oom, cancelled, error
    oom_killed: bool = False
    timed_out: bool = False
    cpu_seconds: float | None = None
    peak_memory_bytes: int | None = None
    pids_peak: int | None = None
    network_rx_bytes: int | None = None
    network_tx_bytes: int | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    worker_id: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of an execution attempt."""

    provenance: ExecutionProvenance
    model_outputs: list[dict]  # Serialized ModelOutput data
    error_message: str | None = None


class ExecutionContext:
    """Context passed to executor containing all info needed to run the benchmark."""

    def __init__(
        self,
        execution_id: UUID,
        attempt_id: UUID,
        attempt_number: int,
        target_model: str,
        benchmark_version_id: UUID,
        dataset_version_id: UUID | None,
        test_cases: list[dict],
        execution_config: dict | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        worker_id: str | None = None,
    ):
        self.execution_id = execution_id
        self.attempt_id = attempt_id
        self.attempt_number = attempt_number
        self.target_model = target_model
        self.benchmark_version_id = benchmark_version_id
        self.dataset_version_id = dataset_version_id
        self.test_cases = test_cases
        self.execution_config = execution_config or {}
        self.correlation_id = correlation_id
        self.trace_id = trace_id
        self.worker_id = worker_id


class Executor(abc.ABC):
    """Abstract executor interface. All execution isolation backends must implement this."""

    @abc.abstractmethod
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """Execute the benchmark in an isolated environment.

        Args:
            context: Full execution context including test cases and configuration.

        Returns:
            ExecutionResult with provenance telemetry and model outputs.

        Raises:
            ExecutorUnavailable: If the required runtime is not available.
            ExecutorTimeout: If the execution exceeds time limits.
            ExecutorError: For other execution failures.
        """
        pass

    @abc.abstractmethod
    async def is_available(self) -> bool:
        """Check if this executor's runtime is available.

        Returns:
            True if the executor can run workloads, False otherwise.
        """
        pass

    @property
    @abc.abstractmethod
    def executor_type(self) -> str:
        """Unique identifier for this executor type (e.g., 'local', 'docker')."""
        pass


class ExecutorUnavailable(Exception):
    """Raised when the required executor runtime is not available."""

    pass


class ExecutorTimeout(Exception):
    """Raised when execution exceeds configured time limits."""

    pass


class ExecutorError(Exception):
    """Raised for general executor failures."""

    pass


class ExecutorRegistry:
    """Registry for available executors. Used for configuration-driven selection."""

    def __init__(self):
        self._executors: dict[str, Executor] = {}

    def register(self, executor: Executor) -> None:
        self._executors[executor.executor_type] = executor

    def get(self, executor_type: str) -> Executor | None:
        return self._executors.get(executor_type)

    def get_default(self) -> Executor:
        """Get the default executor for the current environment.

        Production REQUIRES docker: a missing docker executor raises instead of
        silently falling back to local execution (no-host-execution invariant).
        Development prefers local, falling back to docker.
        """
        from apps.backend.config import settings

        if settings.environment == "production":
            executor = self.get("docker")
            if executor is None:
                raise ExecutorUnavailable(
                    "ENVIRONMENT=production requires the DockerExecutor, but it is not "
                    "registered. Refusing to fall back to LocalExecutor."
                )
            return executor
        dev_executor = self.get("local") or self.get("docker")
        if dev_executor is None:
            raise ExecutorUnavailable(
                "No executor registered. Configure at least one executor "
                "(local in development, docker in production)."
            )
        return dev_executor

    @property
    def registered_types(self) -> list[str]:
        """Executor types currently registered (no availability claim)."""
        return list(self._executors.keys())


# Global registry instance
executor_registry = ExecutorRegistry()
