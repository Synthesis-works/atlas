from typing import Any, Protocol

from atlas_db.models.execution import EventType


class EventPublisher(Protocol):
    def publish_event(
        self,
        run_id: str | None,
        event_type: EventType,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publishes a run event to the configured event bus."""
        ...


class PostgresEventPublisher:
    """A publisher that persists events to the database using the same transaction."""

    def __init__(self, db_session):
        self.db = db_session

    def publish_event(
        self,
        run_id: str | None,
        event_type: EventType,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        import uuid

        from atlas_db.models.execution import RunEvent

        event = RunEvent(
            atlas_run_id=uuid.UUID(str(run_id)) if run_id else None,
            type=event_type,
            message=message,
            metadata_=metadata,
        )
        self.db.add(event)
