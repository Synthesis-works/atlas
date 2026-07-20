import pytest
import uuid
import sys
import os

# Ensure the parent directory is in sys.path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../packages/database')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from atlas_db.core.base import Base

from atlas_db.models.execution import (
    AtlasRun, AtlasTask, RunStatus, TaskStatus, EventType, RunEvent, ModelOutput
)
from app.commands.task import (
    ClaimTasksCommand, CompleteTaskCommand, FailTaskCommand
)
from app.controllers.task_controller import TaskController
from app.events.publisher import PostgresEventPublisher

@pytest.fixture(scope="session")
def engine():
    # We use SQLite for these basic memory tests. 
    # Note: SQLite does not strictly enforce SKIP LOCKED in the same way Postgres does for concurrency,
    # but we can test the functional logic of the state machines and ownership verification.
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

def setup_test_run(db_session, total_tasks=1):
    run_id = uuid.uuid4()
    run = AtlasRun(
        id=run_id,
        session_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        adapter_version_id=uuid.uuid4(),
        target_model="gpt-4",
        status=RunStatus.QUEUED,
        total_tasks=total_tasks
    )
    db_session.add(run)
    
    task_ids = []
    for _ in range(total_tasks):
        task_id = uuid.uuid4()
        task = AtlasTask(
            id=task_id,
            atlas_run_id=run_id,
            test_case_id=uuid.uuid4(),
            status=TaskStatus.PENDING
        )
        db_session.add(task)
        task_ids.append(task_id)
        
    db_session.commit()
    return run_id, task_ids

def test_slice3b_happy_path_and_event_order(db_session):
    run_id, task_ids = setup_test_run(db_session, total_tasks=1)
    task_id = task_ids[0]
    worker_id = uuid.uuid4()
    
    publisher = PostgresEventPublisher(db_session)
    controller = TaskController(db_session, publisher)
    
    # 1. Claim
    cmd_claim = ClaimTasksCommand(worker_id=worker_id, max_tasks=1)
    claimed = controller.execute_claim_tasks(cmd_claim)
    assert len(claimed) == 1
    assert claimed[0] == task_id
    
    run = db_session.query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.RUNNING
    assert run.running_tasks == 1
    
    # 2. Complete
    cmd_complete = CompleteTaskCommand(
        worker_id=worker_id, 
        task_id=task_id, 
        raw_output="{'answer': 42}"
    )
    controller.execute_complete_task(cmd_complete)
    
    run = db_session.query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.COMPLETED
    assert run.running_tasks == 0
    assert run.completed_tasks == 1
    
    # 3. Check Event Order
    events = db_session.query(RunEvent).filter_by(atlas_run_id=run_id).order_by(RunEvent.id).all()
    # Expect: RUN_STARTED -> TASK_ASSIGNED -> TASK_STARTED -> TASK_COMPLETED -> RUN_COMPLETED
    event_types = [e.type for e in events]
    assert EventType.TASK_ASSIGNED in event_types
    assert EventType.TASK_STARTED in event_types
    assert EventType.TASK_COMPLETED in event_types
    
    # Ensure TASK_CLAIMED(ASSIGNED) -> STARTED -> COMPLETED order
    idx_assigned = event_types.index(EventType.TASK_ASSIGNED)
    idx_started = event_types.index(EventType.TASK_STARTED)
    idx_completed = event_types.index(EventType.TASK_COMPLETED)
    assert idx_assigned < idx_started < idx_completed

def test_slice3b_double_claim(db_session):
    run_id, task_ids = setup_test_run(db_session, total_tasks=1)
    worker_a = uuid.uuid4()
    worker_b = uuid.uuid4()
    
    publisher = PostgresEventPublisher(db_session)
    controller = TaskController(db_session, publisher)
    
    # Worker A claims
    claimed_a = controller.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_a, max_tasks=1))
    assert len(claimed_a) == 1
    
    # Worker B tries to claim
    claimed_b = controller.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_b, max_tasks=1))
    assert len(claimed_b) == 0 # Cannot claim because it's already RUNNING

def test_slice3b_ownership_mismatch(db_session):
    run_id, task_ids = setup_test_run(db_session, total_tasks=1)
    task_id = task_ids[0]
    worker_a = uuid.uuid4()
    worker_b = uuid.uuid4() # Imposter
    
    publisher = PostgresEventPublisher(db_session)
    controller = TaskController(db_session, publisher)
    
    # Worker A claims
    controller.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_a, max_tasks=1))
    
    # Worker B tries to complete
    cmd_complete = CompleteTaskCommand(
        worker_id=worker_b, 
        task_id=task_id, 
        raw_output="hacked"
    )
    with pytest.raises(PermissionError):
        controller.execute_complete_task(cmd_complete)

def test_slice3b_failure(db_session):
    run_id, task_ids = setup_test_run(db_session, total_tasks=1)
    task_id = task_ids[0]
    worker_id = uuid.uuid4()
    
    publisher = PostgresEventPublisher(db_session)
    controller = TaskController(db_session, publisher)
    
    # Worker claims
    controller.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_id, max_tasks=1))
    
    # Worker fails
    cmd_fail = FailTaskCommand(
        worker_id=worker_id,
        task_id=task_id,
        error_code="RATE_LIMIT",
        error_message="429 Too Many Requests",
        retryable=True
    )
    controller.execute_fail_task(cmd_fail)
    
    task = db_session.query(AtlasTask).filter_by(id=task_id).one()
    assert task.status == TaskStatus.FAILED
    assert task.error_code == "RATE_LIMIT"
    
    run = db_session.query(AtlasRun).filter_by(id=run_id).one()
    assert run.failed_tasks == 1
    assert run.status == RunStatus.COMPLETED # Because total_tasks=1 and it failed
