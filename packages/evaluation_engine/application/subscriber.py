import structlog
from atlas_db.core.session import SessionLocal

from packages.evaluation_engine.application.service import EvaluationAppService
from packages.evaluation_engine.domain.registry import EvaluationRegistry
from packages.evaluation_engine.infrastructure.artifact_store import LocalArtifactStore
from packages.execution_engine.application.interfaces import EventSubscriber
from packages.execution_engine.application.subscribers import CompositeEventPublisher
from packages.execution_engine.domain.events import DomainEvent, ExecutionCompletedEvent

logger = structlog.get_logger(__name__)


class EvaluationSubscriber(EventSubscriber):
    """
    Subscribes to ExecutionCompletedEvent and triggers the Evaluation Engine.
    """

    def __init__(self):
        # The registry explicitly registers evaluators dynamically in the Celery worker payload.
        # This prevents locking the Outbox synchronously while evaluating.
        pass

    def handle(self, event: DomainEvent) -> None:
        if isinstance(event, ExecutionCompletedEvent):
            logger.info(
                "EvaluationSubscriber received ExecutionCompletedEvent, enqueuing evaluation celery task",
                execution_id=str(event.execution_id),
            )

            # Enqueue the celery task, breaking synchronous execution inline outbox sweep
            from apps.backend.worker.evaluation_tasks import run_evaluation_task

            try:
                run_evaluation_task.delay(str(event.execution_id))
            except Exception as e:
                logger.error("Failed to enqueue evaluation task", execution_id=str(event.execution_id), exc_info=True)
                raise e
