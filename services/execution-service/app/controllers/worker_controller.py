from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from atlas_db.models.execution import ExecutionWorker, WorkerStatus, EventType
from app.commands.worker import RegisterWorkerCommand, HeartbeatWorkerCommand
from app.events.publisher import EventPublisher

class WorkerController:
    """
    Manages the Execution Worker lifecycle.
    Only allows workers to be registered, marked ready, or heartbeat.
    """
    def __init__(self, db: Session, event_publisher: EventPublisher):
        self.db = db
        self.event_publisher = event_publisher
        
    def execute_register_worker(self, cmd: RegisterWorkerCommand) -> UUID:
        """Handles RegisterWorkerCommand"""
        new_worker = ExecutionWorker(
            adapter_id=cmd.adapter_id,
            name=cmd.name,
            version=cmd.version,
            hostname=cmd.hostname,
            platform=cmd.platform,
            region=cmd.region,
            hardware_info=cmd.hardware_info,
            capabilities=cmd.capabilities,
            status=WorkerStatus.READY, # We assume worker is READY upon successful registration
            current_load=0,
            health="healthy",
            last_heartbeat_at=datetime.now(timezone.utc)
        )
        self.db.add(new_worker)
        self.db.flush()
        
        self.db.commit()
        return new_worker.id
        
    def execute_heartbeat(self, cmd: HeartbeatWorkerCommand) -> None:
        """Handles HeartbeatWorkerCommand"""
        # Pessimistic lock on worker
        worker = self.db.query(ExecutionWorker).filter_by(id=cmd.worker_id).with_for_update().one_or_none()
        if not worker:
            raise ValueError(f"Worker {cmd.worker_id} not found.")
            
        worker.last_heartbeat_at = datetime.now(timezone.utc)
        worker.current_load = cmd.current_load
        worker.health = cmd.health
        
        if worker.status in [WorkerStatus.UNHEALTHY, WorkerStatus.OFFLINE]:
            worker.status = WorkerStatus.READY # Heartbeat returned
            
        self.db.commit()

    def execute_mark_unhealthy(self, worker_id: UUID) -> None:
        worker = self.db.query(ExecutionWorker).filter_by(id=worker_id).with_for_update().one_or_none()
        if worker and worker.status in [WorkerStatus.READY, WorkerStatus.BUSY]:
            worker.status = WorkerStatus.UNHEALTHY
            self.db.commit()

    def execute_mark_offline(self, worker_id: UUID) -> None:
        worker = self.db.query(ExecutionWorker).filter_by(id=worker_id).with_for_update().one_or_none()
        if worker and worker.status != WorkerStatus.OFFLINE:
            worker.status = WorkerStatus.OFFLINE
            self.db.commit()
