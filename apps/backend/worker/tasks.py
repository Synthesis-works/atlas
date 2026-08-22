import datetime
import uuid

import structlog
from atlas_db.core.session import SessionLocal
from celery.exceptions import SoftTimeLimitExceeded

from apps.backend.config import settings
from apps.backend.core.telemetry import NullTelemetrySink
from apps.backend.worker.celery_app import celery_app
from apps.backend.worker.execution_worker import ExecutionWorker
from apps.backend.worker.executor_init import get_executor_for_environment, init_executors
from packages.execution_engine.application.outbox_dispatcher import OutboxDispatcher
from packages.execution_engine.application.subscribers import CompositeEventPublisher

logger = structlog.get_logger(__name__)


# Initialize executors at module load time
init_executors()


class ExecutionQueuedSubscriber:
    """Dispatches run_execution_task when ExecutionQueuedEvent is swept from the outbox."""

    def handle(self, event) -> None:
        event_type_name = type(event).__name__
        if event_type_name == "ExecutionQueuedEvent":
            execution_id = getattr(event, "execution_id", None)
            if execution_id:
                logger.info("Dispatching run_execution_task", execution_id=str(execution_id))
                run_execution_task.delay(str(execution_id))


@celery_app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=3600,  # 1 hour soft limit for executions
    time_limit=3660,  # Hard kill after 1h 1m
)
def run_execution_task(self, execution_id_str: str, correlation_id: str | None = None):
    print("*" * 50)
    print(f"!!! CELERY EXECUTING run_execution_task FOR {execution_id_str}")
    print("*" * 50)
    """
    Celery task to run a benchmark execution.
    Retries on infrastructure/network errors automatically (if configured).
    """
    execution_id = uuid.UUID(execution_id_str)
    logger.info("Starting Execution Task", execution_id=str(execution_id))

    # Backend routing / kill switch. "disabled" must NEVER fall back to local
    # execution: the execution simply stays QUEUED until the backend is
    # re-enabled or explicitly failed.
    backend = settings.execution_backend
    if backend == "disabled":
        logger.warning(
            "Execution dispatch suppressed: EXECUTION_BACKEND=disabled (kill "
            "switch). Execution remains QUEUED.",
            execution_id=str(execution_id),
        )
        return

    try:
        if backend == "github_actions":
            _dispatch_to_github_with_retry_policy(self, execution_id_str, correlation_id)
            return

        # Local docker execution path (Render worker with Docker daemon).
        # The execution worker handles its own session for state transitions
        with SessionLocal() as db:
            executor_type = get_executor_for_environment()
            worker = ExecutionWorker(db, executor_type=executor_type)
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


def _dispatch_to_github_with_retry_policy(
    task_self, execution_id_str: str, correlation_id: str | None
) -> None:
    """Dispatch to GitHub Actions; on final retry exhaustion fail the execution."""
    from apps.backend.worker.github_dispatcher import (
        DuplicateDispatchError,
        ExecutionDispatchError,
        run_github_dispatch,
    )

    from atlas_db.models.execution import Execution, ExecutionStatus

    try:
        with SessionLocal() as db:
            run_github_dispatch(
                db,
                execution_id_str,
                correlation_id,
                token=settings.github_execution_token or "",
                repo=settings.github_execution_repo,
                event_type=settings.github_dispatch_event_type,
            )
    except DuplicateDispatchError:
        # Another dispatcher already reserved this execution - not an error.
        logger.info(
            "Duplicate GitHub dispatch suppressed (active attempt exists)",
            execution_id=execution_id_str,
        )
    except ExecutionDispatchError as exc:
        logger.error(
            "GitHub dispatch failed",
            execution_id=execution_id_str,
            retry_count=task_self.request.retries,
            error=str(exc),
        )
        if task_self.request.retries >= task_self.max_retries:
            with SessionLocal() as db:
                execution = db.get(Execution, uuid.UUID(execution_id_str))
                if execution and execution.status == ExecutionStatus.QUEUED:
                    execution.status = ExecutionStatus.FAILED
                    db.commit()
                    logger.error(
                        "Execution FAILED after exhausting dispatch retries",
                        execution_id=execution_id_str,
                        termination_reason="dispatch_failed",
                    )
            return
        raise task_self.retry(exc=exc, countdown=2**task_self.request.retries)


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
                subscribers=[
                    ExecutionQueuedSubscriber(),
                    EvaluationSubscriber(),
                    SnapshotSubscriber(),
                ],
            )
            dispatcher = OutboxDispatcher(session=db, publisher=publisher)
            processed_count = dispatcher.sweep()
            if processed_count > 0:
                logger.info(f"Outbox sweep processed {processed_count} messages")
    except Exception:
        logger.error("Outbox sweep failed", exc_info=True)
