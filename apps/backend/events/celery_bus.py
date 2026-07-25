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

    def emit(self, event: ExecutionEvent) -> None:
        logger.info(f"Event emitted: {event.__class__.__name__} for execution {event.execution_id}")

        if isinstance(event, ExecutionCompleted):
            # Evaluation is now outbox-driven via EvaluationSubscriber
            pass

        elif isinstance(event, ExecutionStarted):
            pass  # Hook for future notifications/dashboards

        elif isinstance(event, ExecutionFailed):
            pass  # Hook for future alerts

        elif isinstance(event, ExecutionCancelled):
            pass  # Hook for cleanup or metrics
