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
        from atlas_db.models.authoring import BenchmarkVersion
        from atlas_db.models.evaluation import EvaluationStrategyVersion
        import json

        execution = self.session.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error("Execution not found for evaluation", execution_id=str(execution_id))
            return

        benchmark_version = self.session.query(BenchmarkVersion).filter(BenchmarkVersion.id == execution.benchmark_version_id).first()
        if not benchmark_version or not benchmark_version.evaluation_strategy_id:
            logger.error("No strategy attached to execution", execution_id=str(execution.id))
            return

        strategy_version_id = benchmark_version.evaluation_strategy_id
        strategy_version = self.session.query(EvaluationStrategyVersion).filter(EvaluationStrategyVersion.id == strategy_version_id).first()
        if not strategy_version:
            logger.error("Strategy configuration missing", execution_id=str(execution.id))
            return

        strategy_type = strategy_version.strategy.type

        evaluation_id = uuid.uuid4()
        self._publish_started(evaluation_id, execution_id, strategy_version_id)

        try:
            # 1. Resolve pipeline components
            evaluator, scorer, _ = self.registry.resolve(strategy_type)

            if not execution.model_outputs:
                logger.warning("Execution has no outputs to evaluate", execution_id=str(execution_id))
                return

            # 3. Measurement & Scoring Phase
            context = EvaluatorContext(
                execution_id=execution_id,
                benchmark_version=benchmark_version.version_string,
                dataset_version=str(benchmark_version.primary_dataset_version_id) if benchmark_version.primary_dataset_version_id else "unknown",
                environment="prod",
            )
            evaluator.prepare(context)

            evaluation_results = []
            overall_score_total = 0.0

            for output in execution.model_outputs:
                try:
                    execution_output = json.loads(output.raw_output)
                except json.JSONDecodeError:
                    execution_output = {"completion": output.raw_output}

                raw_measurements = evaluator.evaluate(execution_output)
                evaluator.postprocess(raw_measurements)

                profile = scorer.score(raw_measurements)
                overall_score_total += profile.overall_score

                result = EvaluationResult(
                    id=uuid.uuid4(),
                    model_output_id=output.id,
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
                evaluation_results.append(result)

            self.session.flush()

            # Create ONE Capability Profile for the execution using the first evaluation_id as the anchor
            final_score = overall_score_total / len(evaluation_results) if evaluation_results else 0.0
            db_profile = CapabilityProfile(
                execution_id=execution_id,
                evaluation_id=evaluation_results[0].id,
                strategy_version_id=strategy_version_id,
                profile_version=1,
                overall_score=final_score,
                score_explanation={"overall": final_score},
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
                evaluation_result_id=evaluation_results[0].id,
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
                overall_score=final_score,
                artifact_count=artifact_count,
            )

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
        self.event_publisher.publish([evt])  # type: ignore

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
        self.event_publisher.publish([evt])  # type: ignore

    def _publish_failed(self, eval_id: uuid.UUID, exec_id: uuid.UUID, reason: str):
        evt = EvaluationFailedEvent(
            evaluation_id=eval_id,
            execution_id=exec_id,
            retryable=True,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        self.event_publisher.publish([evt])  # type: ignore
