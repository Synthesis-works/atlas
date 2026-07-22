import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packages/database"))
)

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


from app.commands.evaluation import (
    CancelEvaluationJobCommand,
    CompleteEvaluationAttemptCommand,
    CreateEvaluationJobCommand,
    FailEvaluationAttemptCommand,
    StartEvaluationAttemptCommand,
)
from app.controllers.evaluation_controller import EvaluationController
from app.events.types import EvaluationEventType
from app.pipelines.base import EvaluationResultBundle
from atlas_db.core.base import Base

# Import all models to ensure they are registered with Base.metadata
from atlas_db.models.evaluation import (
    AttemptStatus,
    EvaluationAttempt,
    EvaluationJob,
    EvaluationJobStatus,
)


class InMemoryEventPublisher:
    def __init__(self):
        self.events = []

    def publish_event(self, job_id, event_type, message=None, metadata=None):
        self.events.append(
            {"job_id": job_id, "event_type": event_type, "message": message, "metadata": metadata}
        )


@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_job_lifecycle(db_session):
    publisher = InMemoryEventPublisher()
    controller = EvaluationController(db_session, publisher)

    run_id = uuid.uuid4()
    pipeline_version_id = uuid.uuid4()

    # 1. Create Job
    cmd_create = CreateEvaluationJobCommand(atlas_run_id=run_id)
    job_id = controller.execute_create_evaluation_job(cmd_create)

    job = db_session.query(EvaluationJob).filter_by(id=job_id).one()
    assert job.status == EvaluationJobStatus.PENDING

    assert len(publisher.events) == 1
    assert publisher.events[-1]["event_type"] == EvaluationEventType.EVALUATION_JOB_CREATED

    # 2. Start Attempt
    cmd_start = StartEvaluationAttemptCommand(
        job_id=job_id, pipeline_version_id=pipeline_version_id
    )
    attempt_id = controller.execute_start_evaluation_attempt(cmd_start)

    job = db_session.query(EvaluationJob).filter_by(id=job_id).one()
    assert job.status == EvaluationJobStatus.EVALUATING

    attempt = db_session.query(EvaluationAttempt).filter_by(id=attempt_id).one()
    assert attempt.status == AttemptStatus.RUNNING

    assert publisher.events[-2]["event_type"] == EvaluationEventType.EVALUATION_STARTED
    assert publisher.events[-1]["event_type"] == EvaluationEventType.PIPELINE_STARTED

    # 3. Complete Attempt
    cmd_complete = CompleteEvaluationAttemptCommand(
        attempt_id=attempt_id, result_bundle=EvaluationResultBundle()
    )
    controller.execute_complete_evaluation_attempt(cmd_complete)

    job = db_session.query(EvaluationJob).filter_by(id=job_id).one()
    assert job.status == EvaluationJobStatus.COMPLETED

    attempt = db_session.query(EvaluationAttempt).filter_by(id=attempt_id).one()
    assert attempt.status == AttemptStatus.COMPLETED

    assert publisher.events[-2]["event_type"] == EvaluationEventType.PIPELINE_COMPLETED
    assert publisher.events[-1]["event_type"] == EvaluationEventType.EVALUATION_COMPLETED


def test_attempt_failure(db_session):
    publisher = InMemoryEventPublisher()
    controller = EvaluationController(db_session, publisher)

    run_id = uuid.uuid4()
    pipeline_version_id = uuid.uuid4()

    cmd_create = CreateEvaluationJobCommand(atlas_run_id=run_id)
    job_id = controller.execute_create_evaluation_job(cmd_create)

    cmd_start = StartEvaluationAttemptCommand(
        job_id=job_id, pipeline_version_id=pipeline_version_id
    )
    attempt_id = controller.execute_start_evaluation_attempt(cmd_start)

    # Fail Attempt
    cmd_fail = FailEvaluationAttemptCommand(attempt_id=attempt_id, error_message="Pipeline Error")
    controller.execute_fail_evaluation_attempt(cmd_fail)

    job = db_session.query(EvaluationJob).filter_by(id=job_id).one()
    assert job.status == EvaluationJobStatus.FAILED

    attempt = db_session.query(EvaluationAttempt).filter_by(id=attempt_id).one()
    assert attempt.status == AttemptStatus.FAILED
    assert attempt.error_message == "Pipeline Error"

    assert publisher.events[-1]["event_type"] == EvaluationEventType.EVALUATION_FAILED


def test_cancel_job(db_session):
    publisher = InMemoryEventPublisher()
    controller = EvaluationController(db_session, publisher)

    run_id = uuid.uuid4()
    pipeline_version_id = uuid.uuid4()

    cmd_create = CreateEvaluationJobCommand(atlas_run_id=run_id)
    job_id = controller.execute_create_evaluation_job(cmd_create)

    cmd_start = StartEvaluationAttemptCommand(
        job_id=job_id, pipeline_version_id=pipeline_version_id
    )
    attempt_id = controller.execute_start_evaluation_attempt(cmd_start)

    # Cancel Job
    cmd_cancel = CancelEvaluationJobCommand(job_id=job_id)
    controller.execute_cancel_evaluation_job(cmd_cancel)

    job = db_session.query(EvaluationJob).filter_by(id=job_id).one()
    assert job.status == EvaluationJobStatus.ABORTED

    attempt = db_session.query(EvaluationAttempt).filter_by(id=attempt_id).one()
    assert attempt.status == AttemptStatus.FAILED
    assert attempt.error_message == "Job cancelled."

    assert publisher.events[-1]["event_type"] == EvaluationEventType.EVALUATION_CANCELLED

    # No further attempts allowed
    with pytest.raises(ValueError, match="Cannot start attempt for job"):
        cmd_start2 = StartEvaluationAttemptCommand(
            job_id=job_id, pipeline_version_id=pipeline_version_id
        )
        controller.execute_start_evaluation_attempt(cmd_start2)


def test_concurrent_attempts(db_session):
    publisher = InMemoryEventPublisher()
    controller = EvaluationController(db_session, publisher)

    run_id = uuid.uuid4()
    pipeline_version_id = uuid.uuid4()

    cmd_create = CreateEvaluationJobCommand(atlas_run_id=run_id)
    job_id = controller.execute_create_evaluation_job(cmd_create)

    # Start First Attempt
    cmd_start1 = StartEvaluationAttemptCommand(
        job_id=job_id, pipeline_version_id=pipeline_version_id
    )
    controller.execute_start_evaluation_attempt(cmd_start1)

    # Attempt to start a second attempt concurrently
    with pytest.raises(ValueError, match="while another attempt is running"):
        cmd_start2 = StartEvaluationAttemptCommand(
            job_id=job_id, pipeline_version_id=pipeline_version_id
        )
        controller.execute_start_evaluation_attempt(cmd_start2)
