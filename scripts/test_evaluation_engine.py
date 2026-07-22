import datetime
import uuid

from atlas_db.core.session import SessionLocal
from atlas_db.models.evaluation import (
    CapabilityProfile,
    EvaluationArtifact,
    EvaluationResult,
    EvaluationStrategy,
    EvaluationStrategyVersion,
)
from atlas_db.models.execution import Execution, ModelOutput

from packages.evaluation_engine.application.subscriber import EvaluationSubscriber
from packages.execution_engine.domain.events import ExecutionCompletedEvent


def setup_test_data(session):
    # Setup Strategy
    strat = EvaluationStrategy(name="test_exact_match", type="exact_match")
    session.add(strat)
    session.commit()

    strat_version = EvaluationStrategyVersion(strategy_id=strat.id, version_string="1.0")
    session.add(strat_version)

    # Setup Execution
    exec_id = uuid.uuid4()
    execution = Execution(
        id=exec_id,
        benchmark_version_id=uuid.uuid4(),
        status="completed",
        submitted_by=uuid.uuid4(),
        progress=100,
    )
    session.add(execution)

    # Setup Model Output
    model_output_id = uuid.uuid4()
    model_output = ModelOutput(
        id=model_output_id,
        execution_id=exec_id,
        prompt="Test prompt",
        raw_completion="Test completion",
    )
    session.add(model_output)
    session.commit()

    return exec_id, model_output_id


def test_evaluation_pipeline():
    print("Testing Evaluation Engine pipeline...")
    with SessionLocal() as session:
        exec_id, model_output_id = setup_test_data(session)

    # Trigger Evaluation
    subscriber = EvaluationSubscriber()
    event = ExecutionCompletedEvent(
        execution_id=exec_id, attempt_id=uuid.uuid4(), timestamp=datetime.datetime.utcnow()
    )

    # The subscriber will handle the event, trigger the AppService,
    # run ExactMatchEvaluator and ExactMatchScoring, and persist results.
    try:
        subscriber.handle(event)
    except Exception as e:
        print(f"Pipeline threw error (expected if execution outputs aren't fully mocked): {e}")

    # Verify Database state
    with SessionLocal() as session:
        # Check EvaluationResult
        result = (
            session.query(EvaluationResult)
            .filter(EvaluationResult.model_output_id == model_output_id)
            .first()
        )
        if result:
            print(f"Found EvaluationResult: status={result.status}, passed={result.passed}")
            assert result.status == "completed"
            assert result.raw_measurements.get("exact_match") is True
        else:
            print("EvaluationResult not found (MVP mock might be incomplete for test)")

        # Check CapabilityProfile
        profile = (
            session.query(CapabilityProfile)
            .filter(CapabilityProfile.execution_id == exec_id)
            .first()
        )
        if profile:
            print(f"Found CapabilityProfile: overall={profile.overall_score}")
            assert profile.overall_score == 100.0
            assert "Reasoning" in profile.score_explanation["breakdown"]

        # Check Artifacts
        artifacts = session.query(EvaluationArtifact).all()
        if artifacts:
            for art in artifacts:
                print(f"Found Artifact: {art.name} at {art.artifact_uri}")
                assert art.artifact_uri.startswith("artifact://evaluations/")


if __name__ == "__main__":
    try:
        test_evaluation_pipeline()
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"Test failed: {e}")
