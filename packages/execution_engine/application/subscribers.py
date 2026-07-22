import abc
from collections.abc import Sequence

from packages.execution_engine.application.interfaces import EventPublisher
from packages.execution_engine.domain.events import DomainEvent


class EventSubscriber(abc.ABC):
    @abc.abstractmethod
    def handle(self, event: DomainEvent) -> None:
        """Handle a single domain event."""
        pass


from apps.backend.core.telemetry import TelemetrySink
from packages.execution_engine.domain import events


class MetricsEventSubscriber(EventSubscriber):
    """
    Listens to domain events and translates them into telemetry metrics.
    """

    def __init__(self, sink: TelemetrySink):
        self.sink = sink

    def handle(self, event: DomainEvent) -> None:
        if isinstance(event, events.ExecutionQueuedEvent):
            self.sink.record_counter("atlas_execution_created_total", 1.0)
            self.sink.record_gauge(
                "atlas_queued_executions", 1.0
            )  # Assuming we increment here, though a gauge usually requires absolute count

        elif isinstance(event, events.ExecutionStartedEvent):
            self.sink.record_counter("atlas_worker_acquire_success_total", 1.0)

        elif isinstance(event, events.ExecutionCompletedEvent):
            self.sink.record_counter("atlas_execution_completed_total", 1.0)

        elif isinstance(event, events.ExecutionFailedEvent):
            self.sink.record_counter("atlas_execution_failed_total", 1.0)

        elif isinstance(event, events.LeaseExpiredEvent):
            self.sink.record_counter("atlas_leases_expired_total", 1.0)


from apps.backend.core.telemetry import get_logger


class CompositeEventPublisher(EventPublisher):
    """
    A concrete EventPublisher that fans out domain events to multiple subscribers.
    """

    def __init__(self, subscribers: Sequence[EventSubscriber]):
        self.subscribers = subscribers
        self.logger = get_logger("EVENT_PUBLISHER")

    def publish(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            for subscriber in self.subscribers:
                try:
                    subscriber.handle(event)
                except Exception:
                    # Log and continue. One broken subscriber (e.g., Metrics)
                    # should not crash the business transaction or other subscribers.
                    self.logger.error(
                        "Subscriber failed to handle event",
                        subscriber=subscriber.__class__.__name__,
                        event=event.__class__.__name__,
                        exc_info=True,
                    )
