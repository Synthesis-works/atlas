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
        
        # Publish Event
        # Note: Worker events might not be tied to a specific atlas_run_id, 
        # so we pass a dummy or we adjust the event publisher/model to allow null run_id for worker events.
        # Wait, the RunEvent model requires atlas_run_id to not be null. 
        # For system-level worker events, we might need a separate WorkerEvent table or allow atlas_run_id=None.
        # As per the INVARIANTS, "RunEvent payload must always include event_type, run_id, and timestamp".
        # So we might not publish a RunEvent for worker registration, OR we need a dummy run_id.
        # Let's check RunEvent model. `atlas_run_id` is nullable=False.
        # Thus, WORKER_REGISTERED and WORKER_HEARTBEAT cannot be easily written to RunEvent unless tied to a run.
        # For now, we will skip writing to run_events for global worker actions, or just persist the worker.
        
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
        
        # If the worker was offline but is heartbeating again, mark it READY
        if worker.status == WorkerStatus.OFFLINE and cmd.health == "healthy":
            worker.status = WorkerStatus.READY
            
        self.db.commit()

    def mark_offline(self, worker_id: UUID) -> None:
        """Marks a worker as OFFLINE."""
        worker = self.db.query(ExecutionWorker).filter_by(id=worker_id).with_for_update().one_or_none()
        if worker and worker.status != WorkerStatus.OFFLINE:
            worker.status = WorkerStatus.OFFLINE
            self.db.commit()
