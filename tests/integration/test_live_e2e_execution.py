import os
import uuid
from datetime import datetime, UTC
from unittest.mock import patch
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.adapters.real import RealModelAdapter
from apps.backend.worker.execution_worker import ExecutionWorker
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.core import Base, Organization, Project, User
from atlas_db.models.evaluation import CapabilityProfile, EvaluationResult, EvaluationStatus
from atlas_db.models.execution import Execution, ExecutionStatus, ModelOutput
from atlas_db.models.tasks import Prompt as DBTaskPrompt, Task, TestCase as DBTestCase
from packages.evaluation_engine.application.subscriber import EvaluationSubscriber
from packages.execution_engine.domain.events import ExecutionCompletedEvent


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY") and not os.getenv("MISTRAL_API_KEY"),
    reason="Live provider API key required in environment"
)
def test_live_provider_e2e_execution(db_session):
    """
    Tests complete end-to-end execution against a live external LLM API
    (Groq/Mistral) through RealModelAdapter without mocking HTTP responses.
    """
    target_model = "groq/llama-3.1-8b-instant" if os.getenv("GROQ_API_KEY") else "mistral-small-latest"
    
    # 1. Setup DB Entities
    org = Organization(id=uuid.uuid4(), name="Live Test Org", slug=f"live-org-{uuid.uuid4().hex[:6]}")
    user = User(id=uuid.uuid4(), email=f"live-{uuid.uuid4().hex[:6]}@example.com", full_name="Live User", organization=org)
    project = Project(id=uuid.uuid4(), name="Live Project", slug=f"live-proj-{uuid.uuid4().hex[:6]}", organization=org)
    db_session.add_all([org, user, project])
    db_session.commit()

    benchmark = Benchmark(id=uuid.uuid4(), project_id=project.id, name="Live Bench")
    db_session.add(benchmark)
    db_session.commit()

    benchmark_version = BenchmarkVersion(id=uuid.uuid4(), benchmark_id=benchmark.id, version_string="1.0.0")
    db_session.add(benchmark_version)
    db_session.commit()

    task = Task(id=uuid.uuid4(), benchmark_version_id=benchmark_version.id, name="add_two_numbers")
    db_session.add(task)
    db_session.commit()

    test_case = DBTestCase(id=uuid.uuid4(), task_id=task.id, input_data={"a": 2, "b": 3}, expected_output={"result": 5})
    task_prompt = DBTaskPrompt(id=uuid.uuid4(), task_id=task.id, template="Write a python function def add(a, b): returning the sum of a and b.")
    db_session.add_all([test_case, task_prompt])
    db_session.commit()

    # 2. Verify AdapterFactory resolves RealModelAdapter
    adapter = AdapterFactory.get_adapter(target_model)
    assert isinstance(adapter, RealModelAdapter)

    # 3. Create Execution in QUEUED state
    execution = Execution(
        id=uuid.uuid4(),
        project_id=project.id,
        benchmark_version_id=benchmark_version.id,
        submitted_by_id=user.id,
        target_model=target_model,
        status=ExecutionStatus.QUEUED,
        queued_at=datetime.now(UTC),
    )
    db_session.add(execution)
    db_session.commit()

    # 4. Execute worker task against live provider API
    worker = ExecutionWorker(db_session)
    worker.process(execution.id)

    # 5. Verify Execution & ModelOutput in DB
    db_session.refresh(execution)
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.completed_items == 1

    outputs = db_session.query(ModelOutput).filter(ModelOutput.execution_id == execution.id).all()
    assert len(outputs) == 1
    assert len(outputs[0].raw_output) > 0

    output_id = outputs[0].id
    execution_id = execution.id

    # 6. Run EvaluationSubscriber for ExecutionCompletedEvent against real LLM output
    with patch("packages.evaluation_engine.application.subscriber.SessionLocal", return_value=db_session):
        subscriber = EvaluationSubscriber()
        subscriber.handle(
            ExecutionCompletedEvent(
                execution_id=execution_id,
                attempt_id=uuid.uuid4(),
                timestamp=datetime.now(UTC),
            )
        )

    eval_result = db_session.query(EvaluationResult).filter(EvaluationResult.model_output_id == output_id).first()
    assert eval_result is not None
    assert eval_result.status == EvaluationStatus.COMPLETED

    cap_profile = db_session.query(CapabilityProfile).filter(CapabilityProfile.execution_id == execution_id).first()
    assert cap_profile is not None
    assert cap_profile.overall_score is not None
