from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from atlas_db.models.execution import (
    AtlasTask, AtlasRun, ModelOutput, 
    TaskStatus, RunStatus, EventType, ExecutionWorker
)
from app.commands.task import (
    ClaimTasksCommand, CompleteTaskCommand, 
    FailTaskCommand, ReleaseTaskCommand
)
from app.events.publisher import EventPublisher

class TaskController:
    """
    Manages Task execution lifecycle independently from the Scheduler.
    Responsible for atomic claiming, exclusive ownership, and updates.
    """
    def __init__(self, db: Session, event_publisher: EventPublisher):
        self.db = db
        self.event_publisher = event_publisher

    def execute_claim_tasks(self, cmd: ClaimTasksCommand) -> List[UUID]:
        """
        Atomically claims tasks for a worker using pessimistic locking.
        Ensures a task can only transition from PENDING/QUEUED to RUNNING once.
        """
        # Fetch pending tasks using SKIP LOCKED to avoid blocking concurrently claiming workers
        stmt = (
            select(AtlasTask)
            .where(AtlasTask.status == TaskStatus.PENDING)
            .limit(cmd.max_tasks)
            .with_for_update(skip_locked=True)
        )
        tasks = self.db.execute(stmt).scalars().all()
        
        claimed_task_ids = []
        now = datetime.now(timezone.utc)
        
        for task in tasks:
            # 1. Update Task State
            task.status = TaskStatus.RUNNING
            task.assigned_worker_id = cmd.worker_id
            task.claimed_at = now
            task.started_at = now
            task.lease_expires_at = now + timedelta(minutes=15) # Example lease
            
            # 2. Update Run Progress
            run = self.db.query(AtlasRun).filter_by(id=task.atlas_run_id).with_for_update().one()
            if run.status == RunStatus.QUEUED:
                run.status = RunStatus.RUNNING
                run.started_at = now
                self.event_publisher.publish_event(
                    run_id=str(run.id),
                    event_type=EventType.RUN_STARTED,
                    message="Run started execution."
                )
                
            run.running_tasks += 1
            
            # 3. Publish Task Events chronologically
            self.event_publisher.publish_event(
                run_id=str(task.atlas_run_id),
                event_type=EventType.TASK_ASSIGNED,
                message=f"Task assigned to worker {cmd.worker_id}",
                metadata={"task_id": str(task.id), "worker_id": str(cmd.worker_id)}
            )
            
            self.event_publisher.publish_event(
                run_id=str(task.atlas_run_id),
                event_type=EventType.TASK_STARTED,
                message="Task started executing.",
                metadata={"task_id": str(task.id), "worker_id": str(cmd.worker_id)}
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
            raise ValueError(f"Task {cmd.task_id} cannot be completed from state {task.status.value}.")

        now = datetime.now(timezone.utc)
        
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
            tokens_used=cmd.tokens_used
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
            metadata={"task_id": str(task.id), "worker_id": str(cmd.worker_id)}
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

        now = datetime.now(timezone.utc)
        
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
            metadata={"task_id": str(task.id), "worker_id": str(cmd.worker_id), "retryable": cmd.retryable}
        )
        
        self._check_run_completion(run, now)
        self.db.commit()

    def _check_run_completion(self, run: AtlasRun, now: datetime) -> None:
        """Helper to check if all tasks are finished and update Run state."""
        # Simple completion logic for Slice 3B: if running_tasks is 0 and total == completed + failed
        if run.running_tasks == 0 and (run.completed_tasks + run.failed_tasks) == run.total_tasks and run.total_tasks > 0:
            run.status = RunStatus.COMPLETED
            run.completed_at = now
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.RUN_COMPLETED,
                message="Run completed."
            )
