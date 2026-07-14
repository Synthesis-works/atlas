from typing import Protocol, Optional, Dict, Any
from .types import EvaluationEventType

class EvaluationEventPublisher(Protocol):
    def publish_event(
        self, 
        job_id: Optional[str], 
        event_type: EvaluationEventType, 
        message: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publishes an evaluation event to the configured event bus."""
        ...
