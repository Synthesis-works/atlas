import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.controllers.evaluation_controller import EvaluationController
from app.engine.capabilities import CapabilityEngine
from app.engine.metrics import MetricEngine
from app.integration.orchestrator import EvaluationOrchestrator
from atlas_db.core.base import Base
from atlas_db.models.evaluation import (
    AttemptStatus,
    CapabilityProfile,
    CapabilityScore,
    EvaluationAttempt,
    EvaluationJob,
    EvaluationJobStatus,
    EvaluationResult,
    MetricValue,
)
from atlas_db.models.execution import (
    AtlasRun,
    ExecutionAdapter,
    ExecutionAdapterVersion,
    ModelOutput,
    RunStatus,
)
from atlas_db.models.execution import EvaluationSession as ExecSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class InMemoryEventPublisher:
    def __init__(self):
        self.events = []

    def publish_event(self, job_id: str, event_type, message: str = ""):
        self.events.append({"job_id": job_id, "event_type": event_type, "message": message})


@pytest.fixture
def db_session():
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    # Needs SQLite JSONB compilation hook
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def compile_jsonb_sqlite(type_, compiler, **kw):
        return "JSON"

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_evaluation_orchestrator(db_session):
    # Setup mock data in Execution DB
    adapter = ExecutionAdapter(name="test_adapter")
    db_session.add(adapter)
    db_session.flush()

    adapter_version = ExecutionAdapterVersion(adapter_id=adapter.id, version_string="1.0")
    db_session.add(adapter_version)
    db_session.flush()

    project_id = uuid.uuid4()
    exec_session = ExecSession(project_id=project_id, name="Test")
    db_session.add(exec_session)
    db_session.flush()

    benchmark_id = uuid.uuid4()

    run = AtlasRun(
        session_id=exec_session.id,
        benchmark_version_id=benchmark_id,
        adapter_version_id=adapter_version.id,
        target_model="test-model",
        status=RunStatus.COMPLETED,
    )
    db_session.add(run)
    db_session.flush()

    output1 = ModelOutput(
        atlas_run_id=run.id, test_case_id=uuid.uuid4(), raw_output="Success", duration_ms=100
    )
    output2 = ModelOutput(
        atlas_run_id=run.id, test_case_id=uuid.uuid4(), raw_output="Fail", duration_ms=120
    )
    db_session.add(output1)
    db_session.add(output2)
    db_session.commit()

    # Initialize components
    publisher = InMemoryEventPublisher()
    controller = EvaluationController(db_session, publisher)
    metric_engine = MetricEngine()
    capability_engine = CapabilityEngine()

    orchestrator = EvaluationOrchestrator(
        db=db_session,
        controller=controller,
        metric_engine=metric_engine,
        capability_engine=capability_engine,
    )

    # Trigger orchestrator
    orchestrator.handle_run_completed(run.id)

    # Assertions
    job = db_session.query(EvaluationJob).filter_by(atlas_run_id=run.id).one()
    assert job.status == EvaluationJobStatus.COMPLETED

    attempt = db_session.query(EvaluationAttempt).filter_by(job_id=job.id).one()
    assert attempt.status == AttemptStatus.COMPLETED

    result = db_session.query(EvaluationResult).filter_by(attempt_id=attempt.id).one()

    metrics = db_session.query(MetricValue).filter_by(result_id=result.id).all()
    assert len(metrics) > 0  # Should have pass_rate, pass_count

    profile = (
        db_session.query(CapabilityProfile).filter_by(adapter_version_id=adapter_version.id).one()
    )
    scores = db_session.query(CapabilityScore).filter_by(profile_id=profile.id).all()
    assert len(scores) > 0  # Should have Correctness mapped to Coding
