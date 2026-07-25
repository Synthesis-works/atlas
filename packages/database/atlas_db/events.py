import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class DomainEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    aggregate_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


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
    dataset_version_ids: list[uuid.UUID] | None = None
    evaluation_strategy_id: uuid.UUID | None = None


@dataclass
class BenchmarkVersionUpdatedEvent(DomainEvent):
    actor_id: uuid.UUID = field(default_factory=uuid.uuid4)
    dataset_version_ids: list[uuid.UUID] | None = None
    evaluation_strategy_id: uuid.UUID | None = None


@dataclass
class BenchmarkLifecycleTransitionEvent(DomainEvent):
    actor_id: uuid.UUID = field(default_factory=uuid.uuid4)
    from_state: str = ""
    to_state: str = ""
