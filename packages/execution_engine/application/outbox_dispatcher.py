import logging
from typing import List, Dict, Any, Type
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, text
from uuid import UUID

from atlas_db.models.outbox import OutboxMessage
from packages.execution_engine.application.interfaces import EventPublisher
from packages.execution_engine.domain.events import (
    DomainEvent, ExecutionQueuedEvent, ExecutionStartedEvent,
    LeaseExpiredEvent, ExecutionHeartbeatEvent, ExecutionRetryEvent,
    ExecutionFailedEvent, ExecutionCompletedEvent, ExecutionCancelledEvent
)
from apps.backend.core.telemetry import (
    set_correlation_id, set_trace_id, generate_uuidv7, get_logger
)
from apps.backend.config import settings

logger = get_logger("OUTBOX")

# Event Registry to map event types back to classes
EVENT_REGISTRY: Dict[str, Type[DomainEvent]] = {
    "ExecutionQueuedEvent": ExecutionQueuedEvent,
    "ExecutionStartedEvent": ExecutionStartedEvent,
    "LeaseExpiredEvent": LeaseExpiredEvent,
    "ExecutionHeartbeatEvent": ExecutionHeartbeatEvent,
    "ExecutionRetryEvent": ExecutionRetryEvent,
    "ExecutionFailedEvent": ExecutionFailedEvent,
    "ExecutionCompletedEvent": ExecutionCompletedEvent,
    "ExecutionCancelledEvent": ExecutionCancelledEvent,
}

class OutboxDispatcher:
    """
    Background worker that reliably delivers domain events to subscribers.
    """
    MAX_RETRIES = 10
    
    def __init__(self, session: Session, publisher: EventPublisher):
        self.session = session
        self.publisher = publisher
        
    def _deserialize_event(self, event_type: str, payload: dict, occurred_at: datetime) -> DomainEvent:
        event_cls = EVENT_REGISTRY.get(event_type)
        if not event_cls:
            raise ValueError(f"Unknown event type: {event_type}")
            
        # Extract timestamp and other kwargs
        kwargs = payload.copy()
        
        # We need to map string UUIDs back to UUID objects
        # and datetime strings back to datetime objects
        # To be robust, we'll parse known fields based on dataclass annotations,
        # but a simple mapping works since we know the shapes.
        
        # In a real dynamic deserializer, we'd use `from_dict(event_cls, payload)`
        # using a library like dacite. For MVP, we'll do simple conversion.
        for key, val in kwargs.items():
            if isinstance(val, str):
                try:
                    kwargs[key] = UUID(val)
                except ValueError:
                    pass
        
        return event_cls(timestamp=occurred_at, **kwargs)

    def sweep(self) -> int:
        """
        Polls for PENDING or FAILED events that are due for retry.
        Returns the number of messages processed successfully.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Acquire lock on batch
        stmt = (
            select(OutboxMessage)
            .where(
                and_(
                    OutboxMessage.status.in_(["PENDING", "FAILED"]),
                    OutboxMessage.next_retry_at <= now
                )
            )
            .order_by(OutboxMessage.created_at.asc())
            .limit(settings.outbox_batch_size)
            .with_for_update(skip_locked=True)
        )
        
        messages = self.session.execute(stmt).scalars().all()
        if not messages:
            return 0
            
        processed_count = 0
            
        # 2. Dispatch events
        for msg in messages:
            # Restore telemetry context
            trace_ctx = msg.trace_context or {}
            if "correlation_id" in trace_ctx:
                set_correlation_id(trace_ctx["correlation_id"])
            if "trace_id" in trace_ctx:
                set_trace_id(trace_ctx["trace_id"])
                
            try:
                # Deserialize
                event = self._deserialize_event(msg.event_type, msg.payload, msg.occurred_at)
                
                # Publish
                self.publisher.publish([event])
                
                # Mark as processed
                msg.status = "PROCESSED"
                msg.processed_at = now
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to dispatch outbox message {msg.outbox_message_id}", exc_info=True)
                
                # Calculate exponential backoff: (2 ^ retry_count) seconds
                msg.retry_count += 1
                if msg.retry_count >= self.MAX_RETRIES:
                    msg.status = "DEAD_LETTER"
                else:
                    msg.status = "FAILED"
                    backoff_seconds = 2 ** msg.retry_count
                    msg.next_retry_at = now + timedelta(seconds=backoff_seconds)
                    
        # 3. Commit the batch updates
        self.session.commit()
        return processed_count
