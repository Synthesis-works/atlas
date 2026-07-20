import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field

@dataclass
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    aggregate_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class BenchmarkCreatedEvent(DomainEvent):
    actor_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)

@dataclass
class BenchmarkVersionCreatedEvent(DomainEvent):
    actor_id: uuid.UUID = field(default_factory=uuid.uuid4)
    benchmark_id: uuid.UUID = field(default_factory=uuid.uuid4)
    version_string: str = ""
    dataset_version_ids: Optional[List[uuid.UUID]] = None
    evaluation_strategy_id: Optional[uuid.UUID] = None

@dataclass
class BenchmarkVersionUpdatedEvent(DomainEvent):
    actor_id: uuid.UUID = field(default_factory=uuid.uuid4)
    dataset_version_ids: Optional[List[uuid.UUID]] = None
    evaluation_strategy_id: Optional[uuid.UUID] = None

@dataclass
class BenchmarkLifecycleTransitionEvent(DomainEvent):
    actor_id: uuid.UUID = field(default_factory=uuid.uuid4)
    from_state: str = ""
    to_state: str = ""
