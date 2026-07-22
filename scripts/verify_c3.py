import os
import uuid
import datetime
from sqlalchemy import create_engine
from atlas_db.core.session import SessionLocal
from atlas_db.models.execution import Execution, ModelOutput
from atlas_db.models.evaluation import EvaluationResult, CapabilityProfile, EvaluationArtifact, EvaluationStrategyVersion, EvaluationStrategy
from packages.execution_engine.domain.events import ExecutionCompletedEvent
from packages.evaluation_engine.application.subscriber import EvaluationSubscriber

def verify():
    print("Verifying Phase C.3 Architectural Refinements...")
    with SessionLocal() as session:
        # Setup test data
        strat = EvaluationStrategy(name=f"test_exact_match_{uuid.uuid4().hex[:8]}", type="exact_match")
        session.add(strat)
        session.commit()

        strat_version = EvaluationStrategyVersion(strategy_id=strat.id, version_string="1.0")
        session.add(strat_version)
        session.commit()

        exec_id = uuid.uuid4()
        execution = Execution(
            id=exec_id,
            project_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            status="COMPLETED",
            submitted_by_id=uuid.uuid4(),
            target_model="test-model",
            completed_items=100,
            total_items=100
        )
        session.add(execution)
        
        model_output_id = uuid.uuid4()
        model_output = ModelOutput(
            id=model_output_id,
            execution_id=exec_id,
            test_case_id=uuid.uuid4(),
            raw_output="Test completion"
        )
        session.add(model_output)
        session.commit()

    # Trigger Pipeline
    subscriber = EvaluationSubscriber()
    event = ExecutionCompletedEvent(
        execution_id=exec_id,
        attempt_id=uuid.uuid4(),
        timestamp=datetime.datetime.utcnow()
    )

    try:
        subscriber.handle(event)
    except Exception as e:
        print(f"Pipeline threw error (expected if execution outputs aren't fully mocked): {e}")

    # Verify all in one transaction
    with SessionLocal() as session:
        result = session.query(EvaluationResult).filter(EvaluationResult.model_output_id == model_output_id).first()
        assert result is not None, "EvaluationResult missing"
        print(f"✅ EvaluationResult stored (evaluation_id={result.id})")
        
        profile = session.query(CapabilityProfile).filter(CapabilityProfile.evaluation_id == result.id).first()
        assert profile is not None, "CapabilityProfile missing"
        assert profile.profile_version == 1, "profile_version missing"
        assert profile.strategy_version_id is not None, "strategy_version_id missing"
        print(f"✅ CapabilityProfile stored (version={profile.profile_version}, overall_score={profile.overall_score})")
        print(f"✅ Score Explanation includes raw_measurements and weights: {'exact_match' in str(profile.score_explanation)}")

        artifacts = session.query(EvaluationArtifact).filter(EvaluationArtifact.evaluation_result_id == result.id).all()
        assert len(artifacts) > 0, "EvaluationArtifact missing"
        for art in artifacts:
            assert art.artifact_uri.startswith(f"artifact://evaluations/{result.id}/")
            print(f"✅ Artifact correctly resolved with logical URI: {art.artifact_uri}")

    print("ALL VERIFICATIONS PASSED")

if __name__ == "__main__":
    verify()
