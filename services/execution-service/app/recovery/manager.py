import logging
from datetime import UTC, datetime, timedelta

from app.events.publisher import EventPublisher
from atlas_db.models.execution import (
    AtlasTask,
    EventType,
    ExecutionWorker,
    TaskStatus,
    WorkerStatus,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RecoveryMetrics(BaseModel):
    leases_expired: int = 0
    workers_unhealthy: int = 0
    workers_offline: int = 0
    recoveries_attempted: int = 0
    recoveries_succeeded: int = 0
    recoveries_skipped: int = 0
    recoveries_failed: int = 0

    def summary(self) -> str:
        return (
            f"Recovery Metrics -> "
            f"Leases Expired: {self.leases_expired}, "
            f"Unhealthy: {self.workers_unhealthy}, "
            f"Offline: {self.workers_offline}, "
            f"Recoveries (Att: {self.recoveries_attempted}, Succ: {self.recoveries_succeeded}, "
            f"Skip: {self.recoveries_skipped}, Fail: {self.recoveries_failed})"
        )


class RecoveryManager:
    """
    Slice 5A: Failure Detection.
    Strictly observes the database for expired leases, unhealthy workers, and dead workers.
    Emits events (facts) but DOES NOT execute recovery transitions or decisions.
    """

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher,
        unhealthy_threshold_seconds: int = 15,
        offline_threshold_seconds: int = 60,
    ):
        self.db = db
        self.event_publisher = event_publisher
        self.unhealthy_threshold = timedelta(seconds=unhealthy_threshold_seconds)
        self.offline_threshold = timedelta(seconds=offline_threshold_seconds)
        self.metrics = RecoveryMetrics()

    def tick(self):
        """
        The main detection loop.
        """
        now = datetime.now(UTC)
        self._detect_expired_leases(now)
        self._detect_unhealthy_workers(now)
        self._detect_offline_workers(now)
        # Note: detect_run_timeouts(now) could also be implemented here

    def _detect_expired_leases(self, now: datetime):
        # Find tasks that are RUNNING but their lease has expired
        tasks = (
            self.db.query(AtlasTask)
            .filter(
                AtlasTask.status == TaskStatus.RUNNING,
                AtlasTask.lease_expires_at != None,
                AtlasTask.lease_expires_at < now,
            )
            .all()
        )

        for task in tasks:
            self.metrics.leases_expired += 1
            self.event_publisher.publish_event(
                run_id=str(task.atlas_run_id),
                event_type=EventType.LEASE_EXPIRED,
                message="Task lease expired.",
                metadata={"task_id": str(task.id), "worker_id": str(task.assigned_worker_id)},
            )
            # In an asynchronous boundary, this event would be picked up by the ExecutionController.
            # In our sync MVP demo, we will invoke the controller directly from the event loop/main script.

    def _detect_unhealthy_workers(self, now: datetime):
        # Workers missing heartbeats beyond unhealthy threshold, but not yet offline threshold
        # and currently in READY or BUSY status.
        unhealthy_time = now - self.unhealthy_threshold
        offline_time = now - self.offline_threshold

        workers = (
            self.db.query(ExecutionWorker)
            .filter(
                ExecutionWorker.status.in_([WorkerStatus.READY, WorkerStatus.BUSY]),
                ExecutionWorker.last_heartbeat_at != None,
                ExecutionWorker.last_heartbeat_at < unhealthy_time,
                ExecutionWorker.last_heartbeat_at >= offline_time,
            )
            .all()
        )

        for worker in workers:
            self.metrics.workers_unhealthy += 1
            # Note: The controller must listen to this fact and update the worker to UNHEALTHY.
            self._emit_worker_event(worker, "Worker marked UNHEALTHY (missed heartbeats).")

    def _detect_offline_workers(self, now: datetime):
        # Workers missing heartbeats beyond the offline threshold
        # (Could be in READY, BUSY, or UNHEALTHY state)
        offline_time = now - self.offline_threshold

        workers = (
            self.db.query(ExecutionWorker)
            .filter(
                ExecutionWorker.status.in_(
                    [WorkerStatus.READY, WorkerStatus.BUSY, WorkerStatus.UNHEALTHY]
                ),
                ExecutionWorker.last_heartbeat_at != None,
                ExecutionWorker.last_heartbeat_at < offline_time,
            )
            .all()
        )

        for worker in workers:
            self.metrics.workers_offline += 1
            self.event_publisher.publish_event(
                run_id=None,  # Worker events are global (unless we link them to a dummy run, but EventPublisher currently requires run_id. Let's pass a placeholder or adapt EventPublisher)
                event_type=EventType.WORKER_OFFLINE,
                message="Worker marked OFFLINE (dead).",
                metadata={"worker_id": str(worker.id)},
            )

    def _emit_worker_event(self, worker: ExecutionWorker, msg: str):
        self.event_publisher.publish_event(
            run_id=None,
            event_type=EventType.WORKER_LOST if "OFFLINE" in msg else EventType.WORKER_HEARTBEAT,
            message=msg,
            metadata={
                "worker_id": str(worker.id),
                "status": "UNHEALTHY" if "UNHEALTHY" in msg else "OFFLINE",
            },
        )
