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
        # In a real app this would be injected via DI container
        self.registry = EvaluationRegistry()
        self.artifact_store = LocalArtifactStore()
        # Wire up a mock exact_match evaluator for MVP
        from packages.evaluation_engine.domain.evaluator import (
            BaseEvaluator,
            EvaluatorContext,
            RawMeasurements,
        )
        from packages.evaluation_engine.domain.scoring import BaseScoringStrategy, CapabilityProfile

        class ExactMatchEvaluator(BaseEvaluator):
            def prepare(self, context: EvaluatorContext) -> None:
                pass

            def evaluate(self, execution_output: dict) -> RawMeasurements:
                return RawMeasurements({"exact_match": True, "latency": 150})

            def postprocess(self, measurements: RawMeasurements) -> None:
                pass

            def cleanup(self) -> None:
                pass

        class ExactMatchScoring(BaseScoringStrategy):
            def score(self, measurements: RawMeasurements) -> CapabilityProfile:
                overall = 100.0 if measurements.raw_data.get("exact_match") else 0.0
                return CapabilityProfile(
                    scores={"Reasoning": overall},
                    overall_score=overall,
                    explanation={
                        "overall": overall,
                        "breakdown": {"Reasoning": overall},
                        "weights": {"Reasoning": 1.0},
                    },
                )

        self.registry.register("exact_match", ExactMatchEvaluator, ExactMatchScoring)

    def handle(self, event: DomainEvent) -> None:
        if isinstance(event, ExecutionCompletedEvent):
            logger.info(
                "EvaluationSubscriber received ExecutionCompletedEvent",
                execution_id=str(event.execution_id),
            )

            with SessionLocal() as db:
                # We need a publisher for the Evaluation events. For MVP we create a local composite
                publisher = CompositeEventPublisher(subscribers=[])

                service = EvaluationAppService(
                    session=db,
                    registry=self.registry,
                    artifact_store=self.artifact_store,
                    event_publisher=publisher,
                )

                service.evaluate_execution(event.execution_id)
                db.commit()
