import uuid
from unittest.mock import Mock, patch

import pytest
from atlas_db.models.authoring import BenchmarkVersion
from atlas_db.models.evaluation import (
    EvaluationStrategy,
    EvaluationStrategyVersion,
    CapabilityProfile,
    EvaluationResult,
)
from atlas_db.models.execution import Execution, ModelOutput, ExecutionStatus

from packages.evaluation_engine.application.service import EvaluationAppService
from packages.evaluation_engine.domain.registry import EvaluationRegistry
from packages.evaluation_engine.infrastructure.artifact_store import LocalArtifactStore
from packages.execution_engine.application.subscribers import CompositeEventPublisher


def test_evaluation_app_service_evaluate_execution():
    from atlas_db.core.session import SessionLocal

    # Since we don't have full test database schema setup here dynamically inside the unit test block,
    # we'll mock the sqlalchemy session to ensure the logic runs smoothly without DB integration.
    # The actual postgres integration is performed by the D1-D5 global regression.

    mock_session = Mock()
    mock_registry = Mock()
    mock_evaluator = Mock()
    mock_scorer = Mock()
    mock_registry.resolve.return_value = (mock_evaluator, mock_scorer, None)

    # Setup the Execution Object
    mock_execution = Execution(
        id=uuid.uuid4(), benchmark_version_id=uuid.uuid4(), status=ExecutionStatus.COMPLETED
    )

    mock_output1 = ModelOutput(
        id=uuid.uuid4(), execution_id=mock_execution.id, raw_output='{"exact_match": true}'
    )
    mock_output2 = ModelOutput(
        id=uuid.uuid4(), execution_id=mock_execution.id, raw_output='{"exact_match": false}'
    )
    mock_execution.model_outputs = [mock_output1, mock_output2]

    # Setup the Benchmark Version
    mock_strategy = EvaluationStrategy(type="exact_match")
    mock_strategy_version = EvaluationStrategyVersion(id=uuid.uuid4(), strategy=mock_strategy)
    mock_benchmark_version = BenchmarkVersion(
        id=mock_execution.benchmark_version_id,
        evaluation_strategy_id=mock_strategy_version.id,
        version_string="1.0",
    )

    def mock_query_side_effect(model):
        qs = Mock()
        if model == Execution:
            qs.filter.return_value.first.return_value = mock_execution
        elif model == BenchmarkVersion:
            qs.filter.return_value.first.return_value = mock_benchmark_version
        elif model == EvaluationStrategyVersion:
            qs.filter.return_value.first.return_value = mock_strategy_version
        return qs

    mock_session.query.side_effect = mock_query_side_effect

    mock_publisher = Mock()

    service = EvaluationAppService(
        session=mock_session,
        registry=mock_registry,
        artifact_store=LocalArtifactStore(),
        event_publisher=mock_publisher,
    )

    from packages.evaluation_engine.domain.evaluator import RawMeasurements
    from packages.evaluation_engine.domain.scoring import (
        CapabilityProfile as DomainCapabilityProfile,
    )

    # configure Mocks
    mock_evaluator.evaluate.return_value = RawMeasurements({"exact_match": True, "latency": 150})
    mock_scorer.score.return_value = DomainCapabilityProfile(
        scores={"Reasoning": 100.0}, overall_score=100.0, explanation={"overall": 100}
    )

    service.evaluate_execution(mock_execution.id)

    assert mock_session.add.call_count == 4  # 2 Results + 1 Profile + 1 Artifact

    # Verify the registry was resolved with the correct DB type
    mock_registry.resolve.assert_called_once_with("exact_match")

    # Verify Evaluator was invoked per model output
    assert mock_evaluator.evaluate.call_count == 2
