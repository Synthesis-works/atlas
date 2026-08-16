from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.commands.task import (
    ClaimTasksCommand,
    CompleteTaskCommand,
    FailTaskCommand,
)
from app.events.publisher import EventPublisher
from app.recovery.policies import RecoveryAction, RecoveryDecisionPolicy
from atlas_db.models.execution import (
    AtlasRun,
    AtlasTask,
    EventType,
    ModelOutput,
    RunStatus,
    TaskStatus,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


class TaskController:
    """
    Manages Task execution lifecycle independently from the Scheduler.
    Responsible for atomic claiming, exclusive ownership, and updates.
    """

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher,
        recovery_policy: RecoveryDecisionPolicy = None,  # type: ignore
    ):
        self.db = db
        self.event_publisher = event_publisher
        self.recovery_policy = recovery_policy

    def execute_claim_tasks(self, cmd: ClaimTasksCommand) -> list[UUID]:
        """
        Atomically claims tasks for a worker using pessimistic locking.
        Ensures a task can only transition from PENDING/QUEUED to RUNNING once.
        """
        # Fetch pending tasks using SKIP LOCKED to avoid blocking concurrently claiming workers
        query = select(AtlasTask).where(AtlasTask.status == TaskStatus.PENDING)

        if cmd.target_task_id:
            query = query.where(AtlasTask.id == cmd.target_task_id)

        stmt = query.limit(cmd.max_tasks).with_for_update(skip_locked=True)
        tasks = self.db.execute(stmt).scalars().all()

        claimed_task_ids = []
        now = datetime.now(UTC)

        for task in tasks:
            # 1. Update Task State
            task.status = TaskStatus.RUNNING
            task.assigned_worker_id = cmd.worker_id
            task.claimed_at = now
            task.started_at = now
            task.lease_expires_at = now + timedelta(minutes=15)  # Example lease

            # 2. Update Run Progress
            run = self.db.query(AtlasRun).filter_by(id=task.atlas_run_id).with_for_update().one()
            if run.status == RunStatus.QUEUED:
                run.status = RunStatus.RUNNING
                run.started_at = now
                self.event_publisher.publish_event(
                    run_id=str(run.id),
                    event_type=EventType.RUN_STARTED,
                    message="Run started execution.",
                )

            run.running_tasks += 1

            # 3. Publish Task Events chronologically
            self.event_publisher.publish_event(
                run_id=str(task.atlas_run_id),
                event_type=EventType.TASK_ASSIGNED,
                message=f"Task assigned to worker {cmd.worker_id}",
                metadata={"task_id": str(task.id), "worker_id": str(cmd.worker_id)},
            )

            self.event_publisher.publish_event(
                run_id=str(task.atlas_run_id),
                event_type=EventType.TASK_STARTED,
                message="Task started executing.",
                metadata={"task_id": str(task.id), "worker_id": str(cmd.worker_id)},
            )

            claimed_task_ids.append(task.id)

        self.db.commit()
        return claimed_task_ids

    def execute_complete_task(self, cmd: CompleteTaskCommand) -> None:
        """Handles successful task completion by a worker."""
        task = self.db.query(AtlasTask).filter_by(id=cmd.task_id).with_for_update().one_or_none()

        if not task:
            raise ValueError(f"Task {cmd.task_id} not found.")

        # Ownership verification
        if task.assigned_worker_id != cmd.worker_id:
            raise PermissionError(f"Worker {cmd.worker_id} does not own task {cmd.task_id}.")

        if task.status != TaskStatus.RUNNING:
            raise ValueError(
                f"Task {cmd.task_id} cannot be completed from state {task.status.value}."
            )

        now = datetime.now(UTC)

        # 1. Update Task
        task.status = TaskStatus.COMPLETED
        task.completed_at = now

        # 2. Create ModelOutput
        output = ModelOutput(
            atlas_run_id=task.atlas_run_id,
            test_case_id=task.test_case_id,
            atlas_task_id=task.id,
            raw_output=cmd.raw_output,
            duration_ms=cmd.duration_ms,
            tokens_used=cmd.tokens_used,
        )
        self.db.add(output)

        # 3. Update Run Progress
        run = self.db.query(AtlasRun).filter_by(id=task.atlas_run_id).with_for_update().one()
        run.running_tasks -= 1
        run.completed_tasks += 1

        self.event_publisher.publish_event(
            run_id=str(run.id),
            event_type=EventType.TASK_COMPLETED,
            message="Task completed successfully.",
            metadata={"task_id": str(task.id), "worker_id": str(cmd.worker_id)},
        )

        self._check_run_completion(run, now)
        self.db.commit()

    def execute_fail_task(self, cmd: FailTaskCommand) -> None:
        """Handles task failure reported by a worker."""
        task = self.db.query(AtlasTask).filter_by(id=cmd.task_id).with_for_update().one_or_none()

        if not task:
            raise ValueError(f"Task {cmd.task_id} not found.")

        if task.assigned_worker_id != cmd.worker_id:
            raise PermissionError(f"Worker {cmd.worker_id} does not own task {cmd.task_id}.")

        now = datetime.now(UTC)

        # 1. Update Task
        task.status = TaskStatus.FAILED
        task.completed_at = now
        task.error_code = cmd.error_code
        task.error_message = cmd.error_message
        task.retryable = cmd.retryable

        # 2. Update Run Progress
        run = self.db.query(AtlasRun).filter_by(id=task.atlas_run_id).with_for_update().one()
        run.running_tasks -= 1
        run.failed_tasks += 1

        self.event_publisher.publish_event(
            run_id=str(run.id),
            event_type=EventType.TASK_FAILED,
            message=f"Task failed: {cmd.error_code} - {cmd.error_message}",
            metadata={
                "task_id": str(task.id),
                "worker_id": str(cmd.worker_id),
                "retryable": cmd.retryable,
            },
        )

        self._check_run_completion(run, now)
        self.db.commit()

    def _check_run_completion(self, run: AtlasRun, now: datetime) -> None:
        """Helper to check if all tasks are finished and update Run state."""
        if run.status == RunStatus.ABORTING:
            if run.running_tasks == 0:
                run.status = RunStatus.CANCELLED
                run.completed_at = now
                self.event_publisher.publish_event(
                    run_id=str(run.id),
                    event_type=EventType.RUN_CANCELLED,
                    message="Run cancelled (all tasks drained).",
                )
        else:
            # Simple completion logic for Slice 3B: if running_tasks is 0 and total == completed + failed
            if (
                run.running_tasks == 0
                and (run.completed_tasks + run.failed_tasks) == run.total_tasks
                and run.total_tasks > 0
            ):
                run.status = RunStatus.COMPLETED
                run.completed_at = now
                self.event_publisher.publish_event(
                    run_id=str(run.id), event_type=EventType.RUN_COMPLETED, message="Run completed."
                )

    def execute_recovery_decision(self, task_id: UUID) -> str:
        """
        Evaluates the recovery policy for a failing task and executes the decision.
        """
        task = self.db.query(AtlasTask).filter_by(id=task_id).with_for_update().one()
        run = self.db.query(AtlasRun).filter_by(id=task.atlas_run_id).with_for_update().one()

        if not self.recovery_policy:
            raise ValueError("No recovery policy configured.")

        action = self.recovery_policy.evaluate_task(task, run)

        if action == RecoveryAction.SKIP:
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.RECOVERY_SKIPPED,
                message="Recovery skipped by policy.",
                metadata={"task_id": str(task.id)},
            )
        elif action == RecoveryAction.RETRY:
            task.status = TaskStatus.QUEUED
            task.assigned_worker_id = None
            task.attempt_number += 1
            task.error_message = None
            task.error_code = None
            task.started_at = None
            task.claimed_at = None
            task.lease_expires_at = None

            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.TASK_REQUEUED,
                message=f"Task requeued for attempt {task.attempt_number}",
                metadata={"task_id": str(task.id), "attempt": task.attempt_number},
            )
        elif action == RecoveryAction.FAIL_TASK:
            task.status = TaskStatus.FAILED
            run.running_tasks -= 1
            run.failed_tasks += 1
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.TASK_FAILED,
                message="Task failed permanently (retries exhausted).",
                metadata={"task_id": str(task.id)},
            )
            self._check_run_completion(run, datetime.now(UTC))
        elif action == RecoveryAction.FAIL_RUN:
            run.status = RunStatus.FAILED
            run.completed_at = datetime.now(UTC)
            task.status = TaskStatus.FAILED
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.RUN_TIMEOUT,
                message="Run failed due to timeout.",
                metadata={"task_id": str(task.id)},
            )

        self.db.commit()
        return action
