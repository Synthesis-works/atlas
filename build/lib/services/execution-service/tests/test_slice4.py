import os
import sys
import uuid

import pytest

# Ensure the parent directory is in sys.path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packages/database"))
)

from app.controllers.task_controller import TaskController
from app.events.publisher import PostgresEventPublisher
from app.scheduler.core import AtlasScheduler
from app.scheduler.policies import (
    CompositePolicy,
    GlobalConcurrencyPolicy,
)
from atlas_db.core.base import Base
from atlas_db.models.execution import (
    AtlasRun,
    AtlasTask,
    ExecutionWorker,
    RunStatus,
    TaskStatus,
    WorkerStatus,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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


def setup_mock_state(db_session):
    # Setup 1 Worker
    worker_id = uuid.uuid4()
    worker = ExecutionWorker(
        id=worker_id, adapter_id=uuid.uuid4(), name="w1", status=WorkerStatus.READY
    )
    db_session.add(worker)

    # Setup Run
    run_id = uuid.uuid4()
    run = AtlasRun(
        id=run_id,
        session_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        adapter_version_id=uuid.uuid4(),
        target_model="gpt-4",
        status=RunStatus.QUEUED,
        total_tasks=3,
    )
    db_session.add(run)

    # Setup Tasks (Mixed priorities)
    t1 = AtlasTask(
        id=uuid.uuid4(),
        atlas_run_id=run_id,
        test_case_id=uuid.uuid4(),
        status=TaskStatus.PENDING,
        priority=0,
    )
    t2 = AtlasTask(
        id=uuid.uuid4(),
        atlas_run_id=run_id,
        test_case_id=uuid.uuid4(),
        status=TaskStatus.PENDING,
        priority=10,
    )  # High priority
    t3 = AtlasTask(
        id=uuid.uuid4(),
        atlas_run_id=run_id,
        test_case_id=uuid.uuid4(),
        status=TaskStatus.PENDING,
        priority=0,
    )

    db_session.add_all([t1, t2, t3])
    db_session.commit()

    return worker_id, [t1.id, t2.id, t3.id]


def test_scheduler_fifo_and_priority(db_session):
    worker_id, task_ids = setup_mock_state(db_session)
    t1, t2, t3 = task_ids

    publisher = PostgresEventPublisher(db_session)
    task_ctrl = TaskController(db_session, publisher)

    # Policy that allows everything
    policy = CompositePolicy([GlobalConcurrencyPolicy(100)])
    scheduler = AtlasScheduler(db_session, task_ctrl, publisher, policy)

    # First tick
    scheduler.tick()

    assert scheduler.metrics.tasks_examined > 0
    assert scheduler.metrics.tasks_scheduled == 3

    # Check that t2 (priority 10) was scheduled first, etc. (we can check db state)
    tasks = db_session.query(AtlasTask).filter(AtlasTask.status == TaskStatus.RUNNING).all()
    assert len(tasks) == 3
    for t in tasks:
        assert t.assigned_worker_id == worker_id


def test_scheduler_concurrency_policy_rejection(db_session):
    worker_id, task_ids = setup_mock_state(db_session)

    publisher = PostgresEventPublisher(db_session)
    task_ctrl = TaskController(db_session, publisher)

    # Restrictive policy (max 1 task globally)
    policy = CompositePolicy([GlobalConcurrencyPolicy(1)])
    scheduler = AtlasScheduler(db_session, task_ctrl, publisher, policy)

    scheduler.tick()

    # Only 1 should be scheduled, 2 should be rejected by policy
    assert scheduler.metrics.tasks_scheduled == 1
    assert scheduler.metrics.policy_rejections == 2

    running = db_session.query(AtlasTask).filter(AtlasTask.status == TaskStatus.RUNNING).count()
    assert running == 1
