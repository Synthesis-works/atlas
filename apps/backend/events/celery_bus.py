import logging

from .bus import (
    ExecutionCancelled,
    ExecutionCompleted,
    ExecutionEvent,
    ExecutionEventBus,
    ExecutionFailed,
    ExecutionStarted,
)

logger = logging.getLogger(__name__)


class CeleryExecutionEventBus(ExecutionEventBus):
    """
    Concrete implementation of Event Bus that enqueues downstream Celery tasks.
    """

    def __init__(self):
        from apps.backend.events.celery_snapshot_dispatcher import CelerySnapshotDispatcher

        self.snapshot_dispatcher = CelerySnapshotDispatcher()

    def emit(self, event: ExecutionEvent) -> None:
        logger.info(f"Event emitted: {event.__class__.__name__} for execution {event.execution_id}")

        if isinstance(event, ExecutionCompleted):
            # Evaluation is now outbox-driven via EvaluationSubscriber.
            # Leaderboard snapshots are triggered safely off EvaluationCompleted events in outbox.
            pass

        elif isinstance(event, ExecutionStarted):
            pass  # Hook for future notifications/dashboards

        elif isinstance(event, ExecutionFailed):
            pass  # Hook for future alerts

        elif isinstance(event, ExecutionCancelled):
            pass  # Hook for cleanup or metrics
