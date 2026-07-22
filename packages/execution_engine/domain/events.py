from dataclasses import dataclass
from datetime import datetime
import uuid
from typing import Optional

@dataclass(frozen=True)
class DomainEvent:
    timestamp: datetime
    
    @property
    def event_type(self) -> str:
        return self.__class__.__name__
        
    @property
    def event_version(self) -> int:
        return 1

    def to_dict(self) -> dict:
        import dataclasses
        data = dataclasses.asdict(self)
        # Convert UUIDs to strings and datetime to isoformat
        def _serialize_val(val):
            if isinstance(val, uuid.UUID):
                return str(val)
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, dict):
                return {k: _serialize_val(v) for k, v in val.items()}
            if isinstance(val, list):
                return [_serialize_val(v) for v in val]
            return val
            
        return {k: _serialize_val(v) for k, v in data.items() if k != "timestamp"}

    
@dataclass(frozen=True)
class ExecutionQueuedEvent(DomainEvent):
    execution_id: uuid.UUID
    benchmark_version_id: uuid.UUID
    submitted_by: uuid.UUID

@dataclass(frozen=True)
class ExecutionStartedEvent(DomainEvent):
    execution_id: uuid.UUID
    attempt_id: uuid.UUID
    worker_id: uuid.UUID

@dataclass(frozen=True)
class LeaseExpiredEvent(DomainEvent):
    execution_id: uuid.UUID
    attempt_id: uuid.UUID
    worker_id: uuid.UUID

@dataclass(frozen=True)
class ExecutionHeartbeatEvent(DomainEvent):
    execution_id: uuid.UUID
    attempt_id: uuid.UUID
    worker_id: uuid.UUID

@dataclass(frozen=True)
class ExecutionRetryEvent(DomainEvent):
    execution_id: uuid.UUID
    attempt_id: uuid.UUID
    error_message: Optional[str]

@dataclass(frozen=True)
class ExecutionFailedEvent(DomainEvent):
    execution_id: uuid.UUID
    attempt_id: uuid.UUID
    error_message: Optional[str]
    will_retry: bool

@dataclass(frozen=True)
class ExecutionCompletedEvent(DomainEvent):
    execution_id: uuid.UUID
    attempt_id: uuid.UUID

@dataclass(frozen=True)
class ExecutionCancelledEvent(DomainEvent):
    execution_id: uuid.UUID
    attempt_id: Optional[uuid.UUID]
