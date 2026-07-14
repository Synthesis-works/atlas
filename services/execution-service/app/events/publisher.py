from typing import Protocol, Optional, Dict, Any
from atlas_db.models.execution import EventType

class EventPublisher(Protocol):
    def publish_event(self, run_id: Optional[str], event_type: EventType, message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Publishes a run event to the configured event bus."""
        ...

class PostgresEventPublisher:
    """A publisher that persists events to the database using the same transaction."""
    def __init__(self, db_session):
        self.db = db_session

    def publish_event(self, run_id: Optional[str], event_type: EventType, message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        from atlas_db.models.execution import RunEvent
        import uuid
        
        event = RunEvent(
            atlas_run_id=uuid.UUID(str(run_id)) if run_id else None,
            type=event_type,
            message=message,
            metadata_=metadata
        )
        self.db.add(event)
