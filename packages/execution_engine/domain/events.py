from dataclasses import dataclass
from datetime import datetime
import uuid
from typing import Optional

@dataclass(frozen=True)
class DomainEvent:
    timestamp: datetime
    
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
