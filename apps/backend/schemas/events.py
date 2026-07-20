from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

class AuditEvent(BaseModel):
    event_id: UUID
    timestamp: datetime
    actor_id: UUID
    resource_type: str
    resource_id: UUID
    action: str
    changes: Optional[dict[str, Any]] = None
