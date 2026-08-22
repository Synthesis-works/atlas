"""Executor initialization and registration.

This module sets up the executor registry with available executors.
Called during worker startup to ensure executors are registered.
"""

from apps.backend.config import settings
from packages.execution_engine.application.docker_executor import DockerExecutor
from packages.execution_engine.application.executor import executor_registry
from packages.execution_engine.application.local_executor import LocalExecutor


def init_executors() -> None:
    """Initialize and register all available executors."""
    # Always register LocalExecutor for development
    local_executor = LocalExecutor()
    executor_registry.register(local_executor)

    # Register DockerExecutor if available (production)
    if settings.environment == "production":
        docker_executor = DockerExecutor()
        executor_registry.register(docker_executor)
    else:
        # In development, optionally register DockerExecutor if Docker is available
        # This allows testing Docker locally
        docker_executor = DockerExecutor()
        # Only register if actually available (will be checked at execution time)
        executor_registry.register(docker_executor)

    _prune_orphan_benchmark_containers()


def _prune_orphan_benchmark_containers() -> int:
    """Best-effort cleanup of exited benchmark containers from prior runs.

    Benchmark containers are labeled ``atlas.benchmark=true`` and never restart,
    so anything left in exited state after a runner crash is garbage. Returns
    the number of removed containers; failures are swallowed (cleanup is
    opportunistic and must never prevent worker startup).
    """
    import logging

    try:
        client = DockerExecutor()._get_client()  # noqa: SLF001 - same-package lifecycle helper
        client.ping()
    except Exception:
        return 0

    removed = 0
    try:
        for container in client.api.containers(
            all=True,
            filters={"label": "atlas.benchmark=true", "status": "exited"},
        ):
            try:
                client.api.remove_container(container["Id"], force=True, v=True)
                removed += 1
            except Exception:
                continue
    except Exception:
        pass

    if removed:
        logging.getLogger(__name__).info("Pruned %d orphan benchmark containers", removed)
    return removed


VALID_ENVIRONMENTS = ("development", "production")


def get_executor_for_environment() -> str:
    """Get the default executor type for the current environment.

    Raises on unknown ENVIRONMENT values: a typo like "prod" must never
    silently downgrade production to local execution.
    """
    if settings.environment not in VALID_ENVIRONMENTS:
        raise ValueError(
            f"ENVIRONMENT={settings.environment!r} is not one of {VALID_ENVIRONMENTS}. "
            "Refusing to guess the executor type."
        )
    if settings.environment == "production":
        return "docker"
    return "local"
