from sqlalchemy.orm import Session
from sqlalchemy import func
from atlas_db.models.execution import ExecutionWorker, AtlasTask, WorkerStatus, TaskStatus
from app.scheduler.core import AtlasScheduler
from app.recovery.manager import RecoveryManager
import time

class HealthService:
    def __init__(self, db: Session, scheduler: AtlasScheduler, recovery: RecoveryManager):
        self.db = db
        self.scheduler = scheduler
        self.recovery = recovery
        self.start_time = time.time()

    def snapshot(self) -> dict:
        # Worker counts
        worker_counts = self.db.query(ExecutionWorker.status, func.count(ExecutionWorker.id)).group_by(ExecutionWorker.status).all()
        workers = {status.value: count for status, count in worker_counts}
        
        ready = workers.get(WorkerStatus.READY.value, 0)
        busy = workers.get(WorkerStatus.BUSY.value, 0)
        offline = workers.get(WorkerStatus.OFFLINE.value, 0)
        unhealthy = workers.get(WorkerStatus.UNHEALTHY.value, 0)

        # Queue counts
        task_counts = self.db.query(AtlasTask.status, func.count(AtlasTask.id)).group_by(AtlasTask.status).all()
        tasks = {status.value: count for status, count in task_counts}
        
        queued = tasks.get(TaskStatus.QUEUED.value, 0) + tasks.get(TaskStatus.PENDING.value, 0)
        running = tasks.get(TaskStatus.RUNNING.value, 0)

        # Check sub-system health statuses based on their last successful loop/action if they have ones, 
        # but for now we consider them healthy if this API can talk to them.
        return {
            "service": "execution",
            "version": "0.5.0",
            "git_tag": "v0.5-platform-core",
            "uptime_seconds": int(time.time() - self.start_time),
            "status": "healthy",
            "scheduler": {
                "status": "healthy",
                "tasks_examined": self.scheduler.metrics.tasks_examined,
                "tasks_scheduled": self.scheduler.metrics.tasks_scheduled,
                "policy_rejections": self.scheduler.metrics.policy_rejections
            },
            "recovery": {
                "status": "healthy",
                "leases_expired": self.recovery.metrics.leases_expired,
                "workers_unhealthy": self.recovery.metrics.workers_unhealthy,
                "workers_offline": self.recovery.metrics.workers_offline
            },
            "workers": {
                "ready": ready,
                "busy": busy,
                "offline": offline,
                "unhealthy": unhealthy
            },
            "queue": {
                "queued": queued,
                "running": running
            }
        }
