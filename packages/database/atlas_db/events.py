import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: Optional[uuid.UUID] = None
    resource_type: str = ""
    resource_id: Optional[uuid.UUID] = None
    action: str = ""
    changes: Dict[str, Any] = field(default_factory=dict)
