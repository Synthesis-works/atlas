import logging
import uuid
from datetime import UTC, datetime

from atlas_db.models.execution import Execution, ExecutionStatus
from atlas_db.models.outbox import OutboxMessage
from sqlalchemy.orm import Session

from apps.backend.events.bus import (
    ExecutionCancelled,
    ExecutionCompleted,
    ExecutionFailed,
    ExecutionStarted,
)
from apps.backend.events.celery_bus import CeleryExecutionEventBus
from apps.backend.worker.execution_runner import ExecutionRunner

logger = logging.getLogger(__name__)


class ExecutionWorker:
    """
    Orchestrates the execution lifecycle: QUEUED -> RUNNING -> COMPLETED/FAILED/CANCELLED/TIMED_OUT.
    """

    def __init__(self, db: Session):
        self.db = db
        self.runner = ExecutionRunner(db)
        self.event_bus = CeleryExecutionEventBus()

    def mark_timed_out(self, execution_id: uuid.UUID, correlation_id: str | None = None):
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if execution and execution.status in (ExecutionStatus.QUEUED, ExecutionStatus.RUNNING):
            execution.status = ExecutionStatus.TIMED_OUT
            self.db.commit()
            self.event_bus.emit(
                ExecutionFailed(
                    execution_id=execution_id,
                    aggregate_id=execution_id,
                    correlation_id=correlation_id,
                    event_time=datetime.now(UTC),
                    error_message="Execution timed out",
                )
            )

    def process(self, execution_id: uuid.UUID, correlation_id: str | None = None):
        from packages.execution_engine.persistence.models import ExecutionModel
        from packages.execution_engine.domain.models import ExecutionState

        core_exec = self.db.query(Execution).filter(Execution.id == execution_id).first()
        ee_exec = self.db.query(ExecutionModel).filter(ExecutionModel.id == execution_id).first()
        execution = core_exec or ee_exec

        if not execution:
            logger.error(f"Execution {execution_id} not found.")
            return

        def update_both_status(status_str: str):
            if core_exec:
                core_exec.status = getattr(ExecutionStatus, status_str, status_str)
            if ee_exec:
                ee_exec.status = getattr(ExecutionState, status_str, status_str)  # type: ignore[arg-type,assignment]
            self.db.commit()

        # Status transition to RUNNING
        if str(execution.status) not in (
            "QUEUED",
            "ExecutionState.QUEUED",
            "ExecutionStatus.QUEUED",
        ):
            logger.warning(
                f"Execution {execution_id} is not QUEUED. Current status: {execution.status}"
            )
            return

        update_both_status("RUNNING")

        self.event_bus.emit(
            ExecutionStarted(
                execution_id=execution_id,
                aggregate_id=execution_id,
                correlation_id=correlation_id,
                event_time=datetime.now(UTC),
            )
        )

        try:
            # 1. Run the execution via Runner
            outputs = self.runner.run(execution)

            # Check for cooperative cancellation
            self.db.refresh(execution)
            if getattr(execution, "cancellation_requested", False):
                update_both_status("CANCELLED")
                self.event_bus.emit(
                    ExecutionCancelled(
                        execution_id=execution_id,
                        aggregate_id=execution_id,
                        correlation_id=correlation_id,
                        event_time=datetime.now(UTC),
                    )
                )
                return

            # 2. Persist ModelOutputs incrementally
            self.db.add_all(outputs)
            self.db.commit()

            # 3. Transition to COMPLETED
            update_both_status("COMPLETED")

        except Exception as e:
            logger.exception(f"Execution {execution_id} failed: {e}")
            self.db.rollback()
            update_both_status("FAILED")
            self.event_bus.emit(
                ExecutionFailed(
                    execution_id=execution_id,
                    aggregate_id=execution_id,
                    correlation_id=correlation_id,
                    event_time=datetime.now(UTC),
                    error_message=str(e),
                )
            )
            return

        # 4. Trigger completion event downstream natively via Outbox
        outbox_msg = OutboxMessage(
            event_id=uuid.uuid4(),
            aggregate_id=execution_id,
            aggregate_type="Execution",
            event_type="ExecutionCompletedEvent",
            event_version=1,
            schema_version=1,
            payload={
                "execution_id": str(execution_id),
                "attempt_id": str(uuid.uuid4())
            },
            trace_context={
                "trace_id": str(correlation_id) if correlation_id else "",
                "correlation_id": str(correlation_id) if correlation_id else ""
            },
            occurred_at=datetime.now(UTC)
        )
        self.db.add(outbox_msg)
        self.db.commit()
