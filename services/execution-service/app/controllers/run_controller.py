from uuid import UUID
from sqlalchemy.orm import Session
from atlas_db.models.execution import AtlasRun, RunStatus, EventType
from app.commands.run import CreateRunCommand, ValidateRunCommand
from app.events.publisher import EventPublisher

class ExecutionController:
    """
    Orchestrates the lifecycle of Execution Runs.
    Strictly owns: state transitions, validation, retry decisions, transactions, and event creation.
    Does NOT own: scheduling, worker allocation, or queuing.
    """
    def __init__(self, db: Session, event_publisher: EventPublisher):
        self.db = db
        self.event_publisher = event_publisher
        
    def execute_create_run(self, cmd: CreateRunCommand) -> UUID:
        """Handles CreateRunCommand"""
        # 1. Create run in CREATED state
        new_run = AtlasRun(
            session_id=cmd.session_id,
            benchmark_version_id=cmd.benchmark_version_id,
            adapter_version_id=cmd.adapter_version_id,
            target_model=cmd.target_model,
            status=RunStatus.CREATED,
            config=cmd.config or {}
        )
        self.db.add(new_run)
        self.db.flush() # flush to get the UUID
        
        # 2. Record Event
        self.event_publisher.publish_event(
            run_id=str(new_run.id),
            event_type=EventType.RUN_CREATED,
            message="Run created successfully."
        )
        
        # Commit the transaction so the run is durably created
        self.db.commit()
        return new_run.id
        
    def execute_validate_run(self, cmd: ValidateRunCommand) -> None:
        """Handles ValidateRunCommand"""
        # 1. Fetch Run (pessimistic lock to prevent race conditions during state transitions)
        run = self.db.query(AtlasRun).filter_by(id=cmd.run_id).with_for_update().one_or_none()
        if not run:
            raise ValueError(f"Run {cmd.run_id} not found.")
            
        if run.status != RunStatus.CREATED:
            raise ValueError(f"Run {cmd.run_id} cannot be validated from state {run.status.value}.")
            
        # 2. Transition to VALIDATING
        run.status = RunStatus.VALIDATING
        self.db.flush()
        
        self.event_publisher.publish_event(
            run_id=str(run.id),
            event_type=EventType.RUN_VALIDATED,
            message="Run validation started."
        )
        
        # (In a real implementation, we would check quotas, permissions, missing datasets here)
        # For Slice 2 MVP, we assume validation succeeds immediately.
        validation_passed = True
        
        if validation_passed:
            run.status = RunStatus.QUEUED
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.RUN_VALIDATED,
                message="Run validation passed. Run is now QUEUED and awaits Scheduler."
            )
        else:
            run.status = RunStatus.FAILED
            run.error_message = "Validation failed: Quota exceeded or missing configuration."
            self.event_publisher.publish_event(
                run_id=str(run.id),
                event_type=EventType.RUN_FAILED,
                message=run.error_message
            )
            
        self.db.commit()
