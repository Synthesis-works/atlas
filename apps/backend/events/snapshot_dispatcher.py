import uuid
from abc import ABC, abstractmethod


class SnapshotDispatcher(ABC):
    """
    Abstract interface for dispatching background snapshot generation tasks.
    This decouples the domain event handlers from the specific background task runner (e.g., Celery).
    """

    @abstractmethod
    def dispatch_benchmark_snapshot(
        self, benchmark_version_id: uuid.UUID, execution_id_trigger: uuid.UUID | None
    ) -> None:
        """Dispatch a background task to rebuild the leaderboard snapshot for a benchmark version."""
        pass

    @abstractmethod
    def dispatch_capability_snapshot(
        self, capability_id: uuid.UUID, execution_id_trigger: uuid.UUID | None
    ) -> None:
        """Dispatch a background task to rebuild the leaderboard snapshot for a capability."""
        pass
