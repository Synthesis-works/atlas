import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from atlas_db.core.base import utcnow
from pydantic import BaseModel, Field


class ExecutionEvent(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_version: str = "1.0"
    event_type: str
    occurred_at: datetime = Field(default_factory=utcnow)
    aggregate_id: uuid.UUID
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    # Legacy compatibility fields
    execution_id: uuid.UUID
    event_time: datetime = Field(default_factory=utcnow)

    class Config:
        arbitrary_types_allowed = True


class ExecutionStarted(ExecutionEvent):
    event_type: str = "ExecutionStarted"


class ExecutionCompleted(ExecutionEvent):
    event_type: str = "ExecutionCompleted"


class ExecutionFailed(ExecutionEvent):
    event_type: str = "ExecutionFailed"
    error_message: str | None = None


class ExecutionCancelled(ExecutionEvent):
    event_type: str = "ExecutionCancelled"


class ExecutionEventBus(ABC):
    """
    Abstract interface for emitting execution events.
    """

    @abstractmethod
    def emit(self, event: ExecutionEvent) -> None:
        pass
