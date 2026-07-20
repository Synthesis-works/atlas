import pytest
import uuid
import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure the parent directory is in sys.path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../packages/database')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from atlas_db.core.base import Base

from atlas_db.models.execution import (
    AtlasRun, AtlasTask, ExecutionWorker, TaskStatus, RunStatus, WorkerStatus
)
from app.recovery.policies import (
    RetryPolicy, TimeoutPolicy, CompositeRecoveryPolicy, RecoveryAction
)
from app.recovery.manager import RecoveryManager
from app.controllers.task_controller import TaskController
from app.controllers.worker_controller import WorkerController
from app.events.publisher import PostgresEventPublisher

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

def setup_mock_state(db_session, past_minutes: int):
    worker_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    past_time = now - timedelta(minutes=past_minutes)
    
    worker = ExecutionWorker(
        id=worker_id, adapter_id=uuid.uuid4(), name="w1", status=WorkerStatus.BUSY,
        last_heartbeat_at=past_time
    )
    db_session.add(worker)
    
    run_id = uuid.uuid4()
    run = AtlasRun(
        id=run_id, session_id=uuid.uuid4(), benchmark_version_id=uuid.uuid4(),
        adapter_version_id=uuid.uuid4(), target_model="gpt-4", status=RunStatus.RUNNING, total_tasks=1, running_tasks=1,
        started_at=past_time
    )
    db_session.add(run)
    
    task_id = uuid.uuid4()
    task = AtlasTask(
        id=task_id, atlas_run_id=run_id, test_case_id=uuid.uuid4(), status=TaskStatus.RUNNING, priority=0,
        assigned_worker_id=worker_id, started_at=past_time, lease_expires_at=past_time + timedelta(minutes=5),
        attempt_number=1
    )
    db_session.add(task)
    db_session.commit()
    
    return worker_id, run_id, task_id

def test_recovery_manager_detection(db_session):
    # Setup state from 20 minutes ago (lease expired, worker offline)
    worker_id, run_id, task_id = setup_mock_state(db_session, past_minutes=20)
    
    publisher = PostgresEventPublisher(db_session)
    recovery_manager = RecoveryManager(db_session, publisher, unhealthy_threshold_seconds=15, offline_threshold_seconds=60)
    
    recovery_manager.tick()
    
    assert recovery_manager.metrics.leases_expired == 1
    assert recovery_manager.metrics.workers_offline == 1

def test_recovery_decision_policy_retry(db_session):
    worker_id, run_id, task_id = setup_mock_state(db_session, past_minutes=20)
    
    publisher = PostgresEventPublisher(db_session)
    policy = CompositeRecoveryPolicy([TimeoutPolicy(3600), RetryPolicy(max_retries=3)])
    task_ctrl = TaskController(db_session, publisher, policy)
    
    action = task_ctrl.execute_recovery_decision(task_id)
    assert action == RecoveryAction.RETRY
    
    # Verify task state mutated correctly
    task = db_session.query(AtlasTask).filter_by(id=task_id).one()
    assert task.status == TaskStatus.QUEUED
    assert task.attempt_number == 2
    assert task.assigned_worker_id is None

def test_recovery_decision_policy_timeout(db_session):
    # Setup state from 2 hours ago (exceeds 3600s timeout)
    worker_id, run_id, task_id = setup_mock_state(db_session, past_minutes=120)
    
    publisher = PostgresEventPublisher(db_session)
    policy = CompositeRecoveryPolicy([TimeoutPolicy(3600), RetryPolicy(max_retries=3)])
    task_ctrl = TaskController(db_session, publisher, policy)
    
    action = task_ctrl.execute_recovery_decision(task_id)
    assert action == RecoveryAction.FAIL_RUN
    
    # Verify run and task state
    run = db_session.query(AtlasRun).filter_by(id=run_id).one()
    task = db_session.query(AtlasTask).filter_by(id=task_id).one()
    
    assert run.status == RunStatus.FAILED
    assert task.status == TaskStatus.FAILED
