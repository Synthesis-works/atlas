import datetime
import uuid

import structlog
from atlas_db.core.session import SessionLocal
from celery.exceptions import SoftTimeLimitExceeded

from apps.backend.core.telemetry import NullTelemetrySink
from apps.backend.worker.celery_app import celery_app
from apps.backend.worker.execution_worker import ExecutionWorker
from packages.execution_engine.application.outbox_dispatcher import OutboxDispatcher
from packages.execution_engine.application.subscribers import CompositeEventPublisher

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=3600,  # 1 hour soft limit for executions
    time_limit=3660,  # Hard kill after 1h 1m
)
def run_execution_task(self, execution_id_str: str, correlation_id: str = None):
    """
    Celery task to run a benchmark execution.
    Retries on infrastructure/network errors automatically (if configured).
    """
    execution_id = uuid.UUID(execution_id_str)
    logger.info("Starting Execution Task", execution_id=str(execution_id))

    try:
        # The execution worker handles its own session for state transitions
        with SessionLocal() as db:
            worker = ExecutionWorker(db)
            worker.process(execution_id, correlation_id=correlation_id)

    except SoftTimeLimitExceeded:
        logger.warning(
            "Execution timed out (SoftTimeLimitExceeded)", execution_id=str(execution_id)
        )
        with SessionLocal() as db:
            worker = ExecutionWorker(db)
            worker.mark_timed_out(execution_id, correlation_id=correlation_id)
        raise

    except Exception as exc:
        dead_letter_payload = {
            "execution_id": str(execution_id),
            "celery_task_id": self.request.id,
            "retry_count": self.request.retries,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "occurred_at": datetime.datetime.utcnow().isoformat(),
        }
        logger.error("Execution task failed", dead_letter=dead_letter_payload, exc_info=True)
        if self.request.retries >= self.max_retries:
            logger.error(
                "Max retries exceeded, execution permanently failed",
                dead_letter=dead_letter_payload,
            )
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@celery_app.task(
    bind=True,
    max_retries=0,  # The sweep handles its own retries of individual events
    time_limit=60,
)
def outbox_sweep_task(self):
    """
    Celery periodic task to process pending outbox events.
    """
    from packages.evaluation_engine.application.subscriber import EvaluationSubscriber
    from apps.backend.events.snapshot_subscriber import SnapshotSubscriber

    try:
        with SessionLocal() as db:
            # Note: We construct a CompositeEventPublisher here.
            # In a real DI container this would be injected.
            publisher = CompositeEventPublisher(
                telemetry_sink=NullTelemetrySink(),
                subscribers=[EvaluationSubscriber(), SnapshotSubscriber()],  # Hook the new evaluation subsystem and Snapshots
            )
            dispatcher = OutboxDispatcher(session=db, publisher=publisher)
            processed_count = dispatcher.sweep()
            if processed_count > 0:
                logger.info(f"Outbox sweep processed {processed_count} messages")
    except Exception:
        logger.error("Outbox sweep failed", exc_info=True)
