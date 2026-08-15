import logging

from atlas_db.core.session import SessionLocal
from atlas_db.models.evaluation import CapabilityProfile, CapabilityScore
from atlas_db.models.execution import Execution

from apps.backend.events.celery_snapshot_dispatcher import CelerySnapshotDispatcher
from packages.evaluation_engine.domain.events import EvaluationCompletedEvent
from packages.execution_engine.application.subscribers import EventSubscriber
from packages.execution_engine.domain.events import DomainEvent

logger = logging.getLogger(__name__)


class SnapshotSubscriber(EventSubscriber):
    """
    Subscribes to finalized asynchronous Evaluation events via the Outbox
    and triggers the Reporting Snapshot dispatcher.
    """

    def __init__(self):
        self.snapshot_dispatcher = CelerySnapshotDispatcher()

    def handle(self, event: DomainEvent) -> None:
        if isinstance(event, EvaluationCompletedEvent):
            logger.info(
                f"SnapshotSubscriber acting on EvaluationCompleted Event for execution {event.execution_id}"
            )
            # Dispatch Snapshot Updates securely
            try:
                with SessionLocal() as db:
                    execution = (
                        db.query(Execution).filter(Execution.id == event.execution_id).first()
                    )
                    if execution:
                        # 1. Update overall benchmark tracking
                        self.snapshot_dispatcher.dispatch_benchmark_snapshot(
                            benchmark_version_id=execution.benchmark_version_id,
                            execution_id_trigger=event.execution_id,
                        )

                        # 2. Update fine-grained capability leaderboards
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
                    f"Failed to dispatch snapshots for validated execution {event.execution_id}: {e}"
                )
                raise
