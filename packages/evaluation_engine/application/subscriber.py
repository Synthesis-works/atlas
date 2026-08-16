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
        print(f"!!! EVALUATION SUBSCRIBER RECEIVED EVENT: {type(event).__name__}")
        if isinstance(event, ExecutionCompletedEvent):
            print(f"!!! MATCHED ExecutionCompletedEvent FOR EXEC_ID: {event.execution_id}")

            # Enqueue the celery task, breaking synchronous execution inline outbox sweep
            from apps.backend.worker.evaluation_tasks import run_evaluation_task

            try:
                print("!!! ENQUEUING EVALUATION TASK...")
                run_evaluation_task.delay(str(event.execution_id))
                print("!!! TASK ENQUEUED SUCESSFULLY ENQUEUED VIA REDIS")
            except Exception as e:
                print(f"!!! FAILED TO ENQUEUE EVALUATION TASK: {e}")
                raise e
