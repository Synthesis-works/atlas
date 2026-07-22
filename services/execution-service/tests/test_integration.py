import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packages/database"))
)

from app.commands.run import CancelRunCommand, CreateRunCommand, ValidateRunCommand
from app.commands.task import CompleteTaskCommand, FailTaskCommand
from app.commands.worker import HeartbeatWorkerCommand, RegisterWorkerCommand
from app.controllers.run_controller import RunController
from app.controllers.task_controller import TaskController
from app.controllers.worker_controller import WorkerController
from app.events.publisher import PostgresEventPublisher
from app.recovery.manager import RecoveryManager
from app.recovery.policies import CompositeRecoveryPolicy, RetryPolicy, TimeoutPolicy
from app.scheduler.core import AtlasScheduler
from app.scheduler.policies import CompositePolicy, GlobalConcurrencyPolicy
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


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def system(db_session):
    publisher = PostgresEventPublisher(db_session)
    run_ctrl = RunController(db_session, publisher)
    worker_ctrl = WorkerController(db_session, publisher)
    recovery_policy = CompositeRecoveryPolicy([TimeoutPolicy(3600), RetryPolicy(max_retries=1)])
    task_ctrl = TaskController(db_session, publisher, recovery_policy)

    sched_policy = CompositePolicy([GlobalConcurrencyPolicy(10)])
    scheduler = AtlasScheduler(db_session, task_ctrl, publisher, sched_policy)
    recovery_manager = RecoveryManager(
        db_session, publisher, unhealthy_threshold_seconds=2, offline_threshold_seconds=5
    )

    return {
        "db": db_session,
        "run_ctrl": run_ctrl,
        "worker_ctrl": worker_ctrl,
        "task_ctrl": task_ctrl,
        "scheduler": scheduler,
        "recovery": recovery_manager,
    }


def test_happy_path(system):
    # Test 1: Happy Path
    run_id = system["run_ctrl"].execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo",
        )
    )
    system["run_ctrl"].execute_validate_run(ValidateRunCommand(run_id=run_id))

    worker_id = system["worker_ctrl"].execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="w1",
            version="1.0",
            hostname="h1",
            platform="linux",
            region="us",
            hardware_info={},
            capabilities={},
        )
    )

    system["scheduler"].tick()

    task = system["db"].query(AtlasTask).filter_by(atlas_run_id=run_id).one()
    assert task.status == TaskStatus.RUNNING

    system["task_ctrl"].execute_complete_task(
        CompleteTaskCommand(worker_id=worker_id, task_id=task.id, raw_output="ok")
    )

    run = system["db"].query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.COMPLETED


def test_worker_failure_and_recovery(system):
    # Test 2: Worker Failure & Recovery
    run_id = system["run_ctrl"].execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo",
        )
    )
    system["run_ctrl"].execute_validate_run(ValidateRunCommand(run_id=run_id))

    worker1_id = system["worker_ctrl"].execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="w1",
            version="1.0",
            hostname="h1",
            platform="linux",
            region="us",
            hardware_info={},
            capabilities={},
        )
    )
    worker2_id = system["worker_ctrl"].execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="w2",
            version="1.0",
            hostname="h2",
            platform="linux",
            region="us",
            hardware_info={},
            capabilities={},
        )
    )

    system["scheduler"].tick()

    task = system["db"].query(AtlasTask).filter_by(atlas_run_id=run_id).one()
    task.lease_expires_at = datetime.now(UTC) - timedelta(seconds=10)
    system["db"].commit()

    system["recovery"].tick()
    system["task_ctrl"].execute_recovery_decision(task.id)

    task = system["db"].query(AtlasTask).filter_by(id=task.id).one()
    assert task.status == TaskStatus.QUEUED
    assert task.attempt_number == 2

    system["scheduler"].tick()
    task = system["db"].query(AtlasTask).filter_by(id=task.id).one()
    # It might pick worker1 or worker2 depending on load. Let's just complete it with whichever was assigned.
    assigned_worker = task.assigned_worker_id
    system["task_ctrl"].execute_complete_task(
        CompleteTaskCommand(worker_id=assigned_worker, task_id=task.id, raw_output="ok")
    )

    run = system["db"].query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.COMPLETED


def test_user_cancellation(system):
    # Test 3: User Cancellation
    run_id = system["run_ctrl"].execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo",
        )
    )
    system["run_ctrl"].execute_validate_run(ValidateRunCommand(run_id=run_id))

    worker_id = system["worker_ctrl"].execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="w1",
            version="1.0",
            hostname="h1",
            platform="linux",
            region="us",
            hardware_info={},
            capabilities={},
        )
    )

    system["scheduler"].tick()

    # Cancel run
    system["run_ctrl"].execute_cancel_run(CancelRunCommand(run_id=run_id))

    run = system["db"].query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.ABORTING

    task = system["db"].query(AtlasTask).filter_by(atlas_run_id=run_id).one()
    system["task_ctrl"].execute_fail_task(
        FailTaskCommand(
            worker_id=worker_id,
            task_id=task.id,
            error_code="ABORTED",
            error_message="cancelled",
            retryable=False,
        )
    )

    run = system["db"].query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.CANCELLED


def test_retry_exhaustion(system):
    # Test 4: Retry Exhaustion
    run_id = system["run_ctrl"].execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo",
        )
    )
    system["run_ctrl"].execute_validate_run(ValidateRunCommand(run_id=run_id))

    worker_id = system["worker_ctrl"].execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="w1",
            version="1.0",
            hostname="h1",
            platform="linux",
            region="us",
            hardware_info={},
            capabilities={},
        )
    )

    system["scheduler"].tick()

    task = system["db"].query(AtlasTask).filter_by(atlas_run_id=run_id).one()

    # Fail 1
    system["task_ctrl"].execute_fail_task(
        FailTaskCommand(
            worker_id=worker_id,
            task_id=task.id,
            error_code="FATAL",
            error_message="err",
            retryable=True,
        )
    )
    system["task_ctrl"].execute_recovery_decision(task.id)

    system["scheduler"].tick()

    # Fail 2 (exhausts max_retries = 1)
    task = system["db"].query(AtlasTask).filter_by(id=task.id).one()
    assigned = task.assigned_worker_id
    system["task_ctrl"].execute_fail_task(
        FailTaskCommand(
            worker_id=assigned,
            task_id=task.id,
            error_code="FATAL",
            error_message="err",
            retryable=True,
        )
    )
    system["task_ctrl"].execute_recovery_decision(task.id)

    run = system["db"].query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.FAILED


def test_recovery_skipped(system):
    # Test 5: Recovery Skipped
    worker_id = system["worker_ctrl"].execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="w1",
            version="1.0",
            hostname="h1",
            platform="linux",
            region="us",
            hardware_info={},
            capabilities={},
        )
    )

    # Miss heartbeat -> Unhealthy
    worker = system["db"].query(ExecutionWorker).filter_by(id=worker_id).one()
    worker.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=3)
    system["db"].commit()

    system["worker_ctrl"].execute_mark_unhealthy(worker_id)
    worker = system["db"].query(ExecutionWorker).filter_by(id=worker_id).one()
    assert worker.status == WorkerStatus.UNHEALTHY

    # Heartbeat returns
    system["worker_ctrl"].execute_heartbeat(
        HeartbeatWorkerCommand(worker_id=worker_id, current_load=0, health="healthy")
    )
    worker = system["db"].query(ExecutionWorker).filter_by(id=worker_id).one()
    assert worker.status == WorkerStatus.READY


def test_cancellation_race(system):
    # Test 6: Cancellation Race
    run_id = system["run_ctrl"].execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo",
        )
    )
    system["run_ctrl"].execute_validate_run(ValidateRunCommand(run_id=run_id))

    worker_id = system["worker_ctrl"].execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="w1",
            version="1.0",
            hostname="h1",
            platform="linux",
            region="us",
            hardware_info={},
            capabilities={},
        )
    )

    system["scheduler"].tick()

    task = system["db"].query(AtlasTask).filter_by(atlas_run_id=run_id).one()

    # Simulating race: user cancels AND worker finishes task back to back
    system["run_ctrl"].execute_cancel_run(CancelRunCommand(run_id=run_id))
    system["task_ctrl"].execute_complete_task(
        CompleteTaskCommand(worker_id=worker_id, task_id=task.id, raw_output="ok")
    )

    # Since the task finished, the running_tasks drops to 0.
    # Because Run was in ABORTING, it transitions to CANCELLED instead of COMPLETED.
    run = system["db"].query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.CANCELLED
