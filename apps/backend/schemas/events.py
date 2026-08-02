from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEvent(BaseModel):
    event_id: UUID
    timestamp: datetime
    actor_id: UUID
    resource_type: str
    resource_id: UUID
    action: str
    changes: dict[str, Any] | None = None
