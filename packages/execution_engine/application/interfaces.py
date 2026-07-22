import abc
from typing import Sequence
from packages.execution_engine.domain.events import DomainEvent

class EventPublisher(abc.ABC):
    @abc.abstractmethod
    def publish(self, events: Sequence[DomainEvent]) -> None:
        """Publishes domain events (e.g., to an outbox or message bus)."""
        pass

class EventSubscriber(abc.ABC):
    @abc.abstractmethod
    def handle(self, event: DomainEvent) -> None:
        pass
