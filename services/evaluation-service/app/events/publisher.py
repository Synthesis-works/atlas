from typing import Any, Protocol

from ..events.event_types import EvaluationEventType


class EvaluationEventPublisher(Protocol):
    def publish_event(
        self,
        job_id: str | None,
        event_type: EvaluationEventType,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publishes an evaluation event to the configured event bus."""
        ...
