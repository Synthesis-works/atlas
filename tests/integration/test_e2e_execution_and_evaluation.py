import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.adapters.real import RealModelAdapter
from apps.backend.worker.execution_worker import ExecutionWorker
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.core import Base, Organization, Project, User
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.evaluation import CapabilityProfile, EvaluationResult, EvaluationStatus
from atlas_db.models.execution import Execution, ExecutionStatus, ModelOutput
from atlas_db.models.tasks import Prompt as DBTaskPrompt, Task, TestCase as DBTestCase
from packages.evaluation_engine.application.subscriber import EvaluationSubscriber
from packages.execution_engine.domain.events import ExecutionCompletedEvent
from packages.execution_engine.persistence import models as ee_persistence_models  # noqa: F401
from packages.llm.models.response import LLMResponse


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def test_e2e_real_adapter_execution_to_evaluation_flow(db_session):
    # 1. Seed Core entities
    user = User(id=uuid.uuid4(), email="tester@example.com", full_name="Test User", is_active=True)
    org = Organization(id=uuid.uuid4(), name="Test Org", slug="test-org")
    project = Project(id=uuid.uuid4(), org_id=org.id, name="Test Project", slug="test-project")
    db_session.add_all([user, org, project])
    db_session.commit()

    # 2. Seed Benchmark, Version, Task, TestCase, TaskPrompt
    benchmark = Benchmark(id=uuid.uuid4(), project_id=project.id, name="HumanEval Lite")
    db_session.add(benchmark)
    db_session.commit()

    benchmark_version = BenchmarkVersion(
        id=uuid.uuid4(), benchmark_id=benchmark.id, version_string="1.0.0"
    )
    db_session.add(benchmark_version)
    db_session.commit()

    dataset = Dataset(id=uuid.uuid4(), project_id=project.id, name="E2E Dataset")
    db_session.add(dataset)
    db_session.commit()

    dataset_version = DatasetVersion(
        id=uuid.uuid4(),
        dataset_id=dataset.id,
        version_string="1.0.0",
        storage_path="storage/datasets/e2e",
    )
    db_session.add(dataset_version)
    db_session.commit()

    task = Task(
        id=uuid.uuid4(),
        benchmark_version_id=benchmark_version.id,
        name="add_two_numbers",
    )
    db_session.add(task)
    db_session.commit()

    test_case = DBTestCase(
        id=uuid.uuid4(),
        task_id=task.id,
        dataset_version_id=dataset_version.id,
        input_data={"a": 2, "b": 3},
        expected_output={"result": 5},
    )
    task_prompt = DBTaskPrompt(
        id=uuid.uuid4(),
        task_id=task.id,
        template="Write a python function def add(a, b): returning the sum of a and b.",
    )
    db_session.add_all([test_case, task_prompt])
    db_session.commit()

    # 3. Create Execution targeting a real provider model ("groq/llama-3.1-8b-instant")
    target_model = "groq/llama-3.1-8b-instant"

    # Verify AdapterFactory resolves RealModelAdapter (not MockModelAdapter)
    adapter = AdapterFactory.get_adapter(target_model)
    assert isinstance(adapter, RealModelAdapter)

    execution = Execution(
        id=uuid.uuid4(),
        project_id=project.id,
        benchmark_version_id=benchmark_version.id,
        dataset_version_id=dataset_version.id,
        submitted_by_id=user.id,
        target_model=target_model,
        status=ExecutionStatus.QUEUED,
        queued_at=datetime.utcnow(),
    )
    db_session.add(execution)
    db_session.commit()

    # 4. Mock the HTTP LLM provider response at the external API boundary
    mock_llm_response = LLMResponse(
        provider="groq",
        model=target_model,
        prompt_tokens=20,
        completion_tokens=30,
        total_tokens=50,
        latency_ms=180,
        response="def add(a, b):\n    return a + b",
        raw={"choices": [{"message": {"content": "def add(a, b):\n    return a + b"}}]},
        created_at=str(datetime.utcnow().timestamp()),
    )

    with (
        patch("packages.llm.clients.groq.GroqClient.health", return_value=True),
        patch(
            "packages.llm.clients.groq.GroqClient.generate",
            return_value=mock_llm_response,
        ),
    ):
        # 5. Run worker execution loop directly with test db session
        worker = ExecutionWorker(db_session)
        worker.process(execution.id)

    # 6. Verify Execution & ModelOutput state in DB
    db_session.refresh(execution)
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.completed_items == 1

    outputs = db_session.query(ModelOutput).filter(ModelOutput.execution_id == execution.id).all()
    assert len(outputs) == 1
    assert outputs[0].raw_output == "def add(a, b):\n    return a + b"
    assert outputs[0].duration_ms == 180
    assert outputs[0].tokens_used == 50

    execution_id = execution.id
    output_id = outputs[0].id

    # 7. Trigger EvaluationSubscriber for ExecutionCompletedEvent
    with patch(
        "packages.evaluation_engine.application.subscriber.SessionLocal", return_value=db_session
    ):
        subscriber = EvaluationSubscriber()
        subscriber.handle(
            ExecutionCompletedEvent(
                execution_id=execution_id,
                attempt_id=uuid.uuid4(),
                timestamp=datetime.utcnow(),
            )
        )

    # 8. Verify EvaluationResult & CapabilityProfile state in DB
    eval_result = (
        db_session.query(EvaluationResult)
        .filter(EvaluationResult.model_output_id == output_id)
        .first()
    )
    assert eval_result is not None
    assert eval_result.status == EvaluationStatus.COMPLETED

    cap_profile = (
        db_session.query(CapabilityProfile)
        .filter(CapabilityProfile.execution_id == execution_id)
        .first()
    )
    assert cap_profile is not None
    assert cap_profile.overall_score == 100.0
