import logging

from app.commands.task import ClaimTasksCommand
from app.controllers.task_controller import TaskController
from app.events.publisher import EventPublisher
from app.scheduler.models import SchedulerMetrics, SchedulingDecision
from app.scheduler.policies import CompositePolicy
from atlas_db.models.execution import (
    AtlasRun,
    AtlasTask,
    EventType,
    ExecutionWorker,
    RunStatus,
    TaskStatus,
    WorkerStatus,
)
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AtlasScheduler:
    def __init__(
        self,
        db: Session,
        task_controller: TaskController,
        event_publisher: EventPublisher,
        policy: CompositePolicy,
    ):
        self.db = db
        self.task_controller = task_controller
        self.event_publisher = event_publisher
        self.policy = policy
        self.metrics = SchedulerMetrics()

    def tick(self):
        """
        The main scheduling loop.
        Follows strict FIFO: ORDER BY priority DESC, created_at ASC
        """
        # Fetch all queued tasks
        tasks = (
            self.db.query(AtlasTask)
            .join(AtlasRun)
            .filter(
                and_(
                    AtlasTask.status == TaskStatus.PENDING,
                    AtlasRun.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]),
                )
            )
            .order_by(AtlasTask.priority.desc(), AtlasTask.created_at.asc())
            .all()
        )

        if not tasks:
            return

        # Fetch global running counts for policies
        global_running = (
            self.db.query(func.count(AtlasTask.id))
            .filter(AtlasTask.status == TaskStatus.RUNNING)
            .scalar()
        )

        for task in tasks:
            self.metrics.record_examined()

            # Fetch model-specific running counts
            model_running = (
                self.db.query(func.count(AtlasTask.id))
                .join(AtlasRun)
                .filter(
                    and_(
                        AtlasTask.status == TaskStatus.RUNNING,
                        AtlasRun.target_model == task.run.target_model,
                    )
                )
                .scalar()
            )

            # Find an available worker (Ordered by load ASC for simple load balancing)
            workers = (
                self.db.query(ExecutionWorker)
                .filter(ExecutionWorker.status == WorkerStatus.READY)
                .order_by(ExecutionWorker.current_load.asc())
                .all()
            )

            if not workers:
                self.metrics.record_no_worker()
                self._emit_deferral_event(task, "No workers available")
                continue

            worker = workers[0]

            # Fetch worker-specific running counts
            worker_running = (
                self.db.query(func.count(AtlasTask.id))
                .filter(
                    and_(
                        AtlasTask.status == TaskStatus.RUNNING,
                        AtlasTask.assigned_worker_id == worker.id,
                    )
                )
                .scalar()
            )

            # Evaluate policies
            if not self.policy.can_schedule(task, global_running, worker_running, model_running):
                self.metrics.record_policy_rejection()
                self._emit_rejection_event(task, "Rejected by Concurrency Policy")
                continue

            # Create SchedulingDecision
            decision = SchedulingDecision(
                task_id=task.id,
                worker_id=worker.id,
                policy="CompositePolicy",
                priority=task.priority,
            )

            # Execute the decision via the TaskController (Atomic Claim)
            success = self._execute_decision(decision)
            if success:
                self.metrics.record_scheduled()
                # Update local counts for next iteration in this tick
                global_running += 1
                model_running += 1
                worker_running += 1
                self._emit_scheduled_event(decision)
            else:
                self.metrics.record_failed_claim()

    def _execute_decision(self, decision: SchedulingDecision) -> bool:
        cmd = ClaimTasksCommand(worker_id=decision.worker_id, max_tasks=1)
        # Using a slight hack for the MVP: The ClaimTasksCommand normally queries PENDING tasks randomly.
        # But we need it to claim THIS specific task atomically.
        # Since we are building an isolated controller, we will add a target_task_id to the claim command.
        cmd.target_task_id = decision.task_id

        claimed = self.task_controller.execute_claim_tasks(cmd)
        return len(claimed) > 0

    def _emit_deferral_event(self, task: AtlasTask, reason: str):
        self.event_publisher.publish_event(
            run_id=str(task.atlas_run_id),
            event_type=EventType.TASK_DEFERRED,
            message=reason,
            metadata={"task_id": str(task.id)},
        )

    def _emit_rejection_event(self, task: AtlasTask, reason: str):
        self.event_publisher.publish_event(
            run_id=str(task.atlas_run_id),
            event_type=EventType.TASK_REJECTED_BY_POLICY,
            message=reason,
            metadata={"task_id": str(task.id)},
        )

    def _emit_scheduled_event(self, decision: SchedulingDecision):
        # We don't necessarily need the run_id here if we just log it, but EventPublisher requires run_id.
        # It's better to fetch it, or just let TaskController emit TASK_ASSIGNED.
        # Since TaskController emits TASK_ASSIGNED, TASK_SCHEDULED is a scheduler-specific event.
        task = self.db.query(AtlasTask).filter_by(id=decision.task_id).one()
        self.event_publisher.publish_event(
            run_id=str(task.atlas_run_id),
            event_type=EventType.TASK_SCHEDULED,
            message="Task scheduled successfully.",
            metadata=decision.model_dump(mode="json"),
        )
