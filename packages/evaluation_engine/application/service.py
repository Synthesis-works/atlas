import uuid
from datetime import datetime

import structlog
from atlas_db.models.evaluation import (
    CapabilityProfile,
    EvaluationArtifact,
    EvaluationResult,
    EvaluationStatus,
)
from atlas_db.models.execution import (
    Execution,  # Ensure model_outputs is available
)
from sqlalchemy.orm import Session

from packages.evaluation_engine.domain.evaluator import EvaluatorContext
from packages.evaluation_engine.domain.events import (
    EvaluationCompletedEvent,
    EvaluationFailedEvent,
    EvaluationStartedEvent,
)
from packages.evaluation_engine.domain.registry import EvaluationRegistry
from packages.evaluation_engine.infrastructure.artifact_store import BaseArtifactStore
from packages.execution_engine.application.interfaces import EventPublisher

logger = structlog.get_logger(__name__)


class EvaluationAppService:
    """
    Orchestrates the evaluation pipeline:
    1. Look up execution outputs
    2. Lookup strategy from registry
    3. Run Evaluator (measurements)
    4. Run ScoringStrategy (capability profiles)
    5. Save results & artifacts
    6. Publish domain events
    """

    def __init__(
        self,
        session: Session,
        registry: EvaluationRegistry,
        artifact_store: BaseArtifactStore,
        event_publisher: EventPublisher,
    ):
        self.session = session
        self.registry = registry
        self.artifact_store = artifact_store
        self.event_publisher = event_publisher

    def evaluate_execution(self, execution_id: uuid.UUID) -> None:
        execution = self.session.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error("Execution not found for evaluation", execution_id=str(execution_id))
            return

        evaluation_id = uuid.uuid4()
        strategy_version_id = (
            uuid.uuid4()
        )  # In a real implementation, fetched from execution.benchmark

        self._publish_started(evaluation_id, execution_id, strategy_version_id)

        try:
            # 1. Resolve pipeline components
            # For the MVP, we hardcode the benchmark type to a generic exact_match to prove the flow
            strategy_type = "exact_match"
            evaluator, scorer, _ = self.registry.resolve(strategy_type)

            # 2. Extract execution outputs
            # Assuming execution has a backref to model_output or similar
            # For now, we mock the outputs
            mock_execution_output = {"completion": "test output"}

            # 3. Measurement Phase
            context = EvaluatorContext(
                execution_id=execution_id,
                benchmark_version="1.0",
                dataset_version="1.0",
                environment="prod",
            )
            evaluator.prepare(context)
            raw_measurements = evaluator.evaluate(mock_execution_output)
            evaluator.postprocess(raw_measurements)

            # 4. Scoring Phase
            profile = scorer.score(raw_measurements)

            # 5. Persist Results
            # Use actual model_output_id if available for the MVP flow
            model_output_id = (
                execution.model_outputs[0].id if execution.model_outputs else uuid.uuid4()
            )
            result = EvaluationResult(
                id=evaluation_id,
                model_output_id=model_output_id,
                strategy_version_id=strategy_version_id,
                status=EvaluationStatus.COMPLETED,
                passed=True if profile.overall_score and profile.overall_score >= 80 else False,
                raw_measurements=raw_measurements.raw_data,
                evaluation_context={
                    "benchmark_version": context.benchmark_version,
                    "dataset_version": context.dataset_version,
                    "environment": context.environment,
                },
            )
            self.session.add(result)
            self.session.flush()

            # Persist Profile
            db_profile = CapabilityProfile(
                execution_id=execution_id,
                evaluation_id=result.id,
                strategy_version_id=strategy_version_id,
                profile_version=1,
                overall_score=profile.overall_score,
                score_explanation=profile.explanation,
                profile_metadata={},
            )
            self.session.add(db_profile)

            artifact_count = 0
            # Example artifact storage (using dummy files for MVP test)
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
                tf.write("test log")
                tf_path = tf.name

            uri = self.artifact_store.store_artifact(evaluation_id, "logs.txt", tf_path)
            artifact_count += 1
            db_artifact = EvaluationArtifact(
                evaluation_result_id=result.id,
                artifact_uri=uri,
                name="logs.txt",
                mime_type="text/plain",
            )
            self.session.add(db_artifact)

            # 6. Publish Completed
            evaluator.cleanup()

            self._publish_completed(
                evaluation_id=evaluation_id,
                execution_id=execution_id,
                overall_score=profile.overall_score,
                artifact_count=artifact_count,
            )

            # Commit handled by caller or Outbox transaction wrapper

        except Exception as e:
            logger.error(
                "Evaluation pipeline failed", execution_id=str(execution_id), exc_info=True
            )
            self._publish_failed(evaluation_id, execution_id, str(e))
            raise e

    def _publish_started(self, eval_id: uuid.UUID, exec_id: uuid.UUID, strategy_id: uuid.UUID):
        evt = EvaluationStartedEvent(
            evaluation_id=eval_id,
            execution_id=exec_id,
            strategy_version_id=strategy_id,
            timestamp=datetime.utcnow(),
        )
        self.event_publisher.publish([evt])

    def _publish_completed(
        self,
        evaluation_id: uuid.UUID,
        execution_id: uuid.UUID,
        overall_score: float,
        artifact_count: int,
    ):
        evt = EvaluationCompletedEvent(
            evaluation_id=evaluation_id,
            execution_id=execution_id,
            overall_score=overall_score,
            duration_ms=100,  # mock duration
            artifact_count=artifact_count,
            timestamp=datetime.utcnow(),
        )
        self.event_publisher.publish([evt])

    def _publish_failed(self, eval_id: uuid.UUID, exec_id: uuid.UUID, reason: str):
        evt = EvaluationFailedEvent(
            evaluation_id=eval_id,
            execution_id=exec_id,
            retryable=True,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        self.event_publisher.publish([evt])
