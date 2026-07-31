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
            # Evaluation is now outbox-driven via EvaluationSubscriber

            # Dispatch Snapshot Updates
            from atlas_db.core.session import SessionLocal
            from atlas_db.models.execution import Execution
            from atlas_db.models.evaluation import CapabilityProfile, CapabilityScore

            try:
                with SessionLocal() as db:
                    execution = (
                        db.query(Execution).filter(Execution.id == event.execution_id).first()
                    )
                    if execution:
                        self.snapshot_dispatcher.dispatch_benchmark_snapshot(
                            benchmark_version_id=execution.benchmark_version_id,
                            execution_id_trigger=event.execution_id,
                        )

                        capability_ids = (
                            db.query(CapabilityScore.capability_id)
                            .join(
                                CapabilityProfile,
                                CapabilityProfile.id == CapabilityScore.capability_profile_id,
                            )
                            .filter(CapabilityProfile.execution_id == event.execution_id)
                            .all()
                        )

                        for row in capability_ids:
                            self.snapshot_dispatcher.dispatch_capability_snapshot(
                                capability_id=row[0], execution_id_trigger=event.execution_id
                            )
            except Exception as e:
                logger.error(
                    f"Failed to dispatch snapshots for execution {event.execution_id}: {e}"
                )

        elif isinstance(event, ExecutionStarted):
            pass  # Hook for future notifications/dashboards

        elif isinstance(event, ExecutionFailed):
            pass  # Hook for future alerts

        elif isinstance(event, ExecutionCancelled):
            pass  # Hook for cleanup or metrics
