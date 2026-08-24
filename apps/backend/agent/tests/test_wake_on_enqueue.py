"""Regression tests for Render worker wake-on-enqueue behavior.

These tests verify that notify_worker_wake() is called after successful
transaction commit when ExecutionQueuedEvent outbox rows are created.
"""

from unittest.mock import MagicMock, patch
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from atlas_db.models.execution import Execution as DBExecution
from atlas_db.models.execution import ExecutionStatus
from apps.backend.agent.tools.execution_tools import RunBenchmarkTool


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@patch("apps.backend.worker.wake_client.notify_worker_wake")
def test_run_benchmark_tool_calls_notify_worker_wake_after_commit(mock_wake, db_session):
    """RunBenchmarkTool.execute() must call notify_worker_wake() after commit
    so the Render worker wakes up to process the outbox event.
    """
    # Create minimal required entities: benchmark, dataset, test_case
    from atlas_db.models.core import Project
    from atlas_db.models.authoring import Benchmark, BenchmarkVersion
    from atlas_db.models.dataset import Dataset, DatasetVersion
    from atlas_db.models.tasks import TestCase

    project = Project(id=uuid.uuid4(), name="Test Project", slug="test-project")
    db_session.add(project)
    db_session.flush()

    benchmark = Benchmark(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Test Benchmark",
        objective="Test",
    )
    db_session.add(benchmark)
    db_session.flush()

    bv = BenchmarkVersion(
        id=uuid.uuid4(),
        benchmark_id=benchmark.id,
        version_string="1.0.0",
        evaluation_strategy_id=uuid.uuid4(),
    )
    db_session.add(bv)
    db_session.flush()

    ds = Dataset(id=uuid.uuid4(), project_id=project.id, name="Test Dataset")
    db_session.add(ds)
    db_session.flush()

    dv = DatasetVersion(
        id=uuid.uuid4(), dataset_id=ds.id, version_string="1.0.0", storage_path="/tmp/test"
    )
    db_session.add(dv)
    db_session.flush()

    tc = TestCase(
        id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        dataset_version_id=dv.id,
        input_data={},
        expected_output={},
    )
    db_session.add(tc)
    db_session.commit()

    tool = RunBenchmarkTool()
    result = tool.execute(
        db=db_session,
        benchmark_version_id=str(bv.id),
        dataset_version_id=str(dv.id),
        target_models=["gemini-3.5-flash-lite"],
        task_id=str(uuid.uuid4()),
    )

    assert result["status"] == "DISPATCHED"
    assert len(result["execution_ids"]) == 1

    # Verify the wake was called exactly once after commit
    mock_wake.assert_called_once()


@patch("apps.backend.worker.wake_client.notify_worker_wake")
def test_stale_attempt_reaper_calls_notify_worker_wake_after_commit(mock_wake, db_session):
    """reap_stale_attempts() must call notify_worker_wake() after commit
    when requeuing executions with fresh ExecutionQueuedEvent outbox rows.
    """
    from apps.backend.worker.stale_attempt_reaper import reap_stale_attempts
    from atlas_db.models.execution import (
        Execution,
        ExecutionAttempt,
        AttemptStatus,
        ExecutionStatus,
    )
    from datetime import UTC, datetime, timedelta

    # Create an execution with a stale attempt
    execution = Execution(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        submitted_by_id=uuid.uuid4(),
        target_model="gemini-3.5-flash-lite",
        status=ExecutionStatus.RUNNING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(execution)
    db_session.flush()

    attempt = ExecutionAttempt(
        id=uuid.uuid4(),
        execution_id=execution.id,
        attempt_number=1,
        status=AttemptStatus.RUNNING,
        executor_type="docker",
        started_at=datetime.now(UTC) - timedelta(minutes=150),
        updated_at=datetime.now(UTC) - timedelta(minutes=150),
    )
    db_session.add(attempt)
    db_session.commit()

    # Reap the stale attempt - should requeue the execution and call wake
    summary = reap_stale_attempts(db_session, max_age_minutes=120)

    assert summary["attempts_reaped"] == 1
    assert summary["executions_requeued"] == 1

    # Verify the wake was called exactly once after commit
    mock_wake.assert_called_once()


@patch("apps.backend.worker.wake_client.notify_worker_wake")
def test_executions_router_create_execution_calls_notify_worker_wake(mock_wake, db_session):
    """POST /benchmarks/{bvid}/executions must call notify_worker_wake() after
    commit (existing behavior, verified here as regression test).
    """
    from packages.execution_engine.application.execution_app_service import (
        ExecutionApplicationService,
    )
    from packages.execution_engine.domain.services import ExecutionService
    from packages.execution_engine.persistence.repository import SqlAlchemyExecutionRepository
    from atlas_db.repositories.authoring import BenchmarkRepository
    from atlas_db.models.core import Project
    from atlas_db.models.authoring import Benchmark, BenchmarkVersion
    from atlas_db.models.dataset import Dataset, DatasetVersion
    from atlas_db.models.tasks import TestCase

    project = Project(id=uuid.uuid4(), name="Test Project", slug="test-project")
    db_session.add(project)
    db_session.flush()

    benchmark = Benchmark(
        id=uuid.uuid4(),
        project_id=project.id,
        name="Test Benchmark",
        objective="Test",
    )
    db_session.add(benchmark)
    db_session.flush()

    bv = BenchmarkVersion(
        id=uuid.uuid4(),
        benchmark_id=benchmark.id,
        version_string="1.0.0",
        evaluation_strategy_id=uuid.uuid4(),
    )
    db_session.add(bv)
    db_session.flush()

    ds = Dataset(id=uuid.uuid4(), project_id=project.id, name="Test Dataset")
    db_session.add(ds)
    db_session.flush()

    dv = DatasetVersion(
        id=uuid.uuid4(), dataset_id=ds.id, version_string="1.0.0", storage_path="/tmp/test"
    )
    db_session.add(dv)
    db_session.flush()

    tc = TestCase(
        id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        dataset_version_id=dv.id,
        input_data={},
        expected_output={},
    )
    db_session.add(tc)
    db_session.commit()

    domain_service = ExecutionService()
    execution_repo = SqlAlchemyExecutionRepository(db_session)
    benchmark_repo = BenchmarkRepository(db_session)
    service = ExecutionApplicationService(domain_service, execution_repo, benchmark_repo)

    execution = service.submit_execution(
        benchmark_version_id=uuid.UUID(str(bv.id)),
        dataset_version_id=uuid.UUID(str(dv.id)),
        submitted_by=uuid.uuid4(),
        target_model="gemini-3.5-flash-lite",
    )

    # The service internally commits (see execution_app_service.py)
    # Verify wake is called
    mock_wake.assert_called_once()


@patch("apps.backend.worker.wake_client.notify_worker_wake")
def test_execution_retry_in_worker_does_not_call_wake(mock_wake, db_session):
    """Execution retry (via expire_lease -> retry) runs inside the worker's
    outbox sweep loop and should NOT call notify_worker_wake() since the
    worker is already awake and processing.
    """
    from packages.execution_engine.domain.services import ExecutionService
    from packages.execution_engine.persistence.repository import SqlAlchemyExecutionRepository
    from packages.execution_engine.domain.models import Execution as DomainExecution
    from packages.execution_engine.domain.models import ExecutionState

    # Create a domain execution in RETRYING state
    domain_exec = DomainExecution(
        id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        created_by=uuid.uuid4(),
        status=ExecutionState.RETRYING,
        target_model="gemini-3.5-flash-lite",
        max_retries=3,
    )
    # Manually set up an attempt that can be retried
    from packages.execution_engine.domain.models import ExecutionAttempt, AttemptStatus, Lease
    from datetime import UTC, datetime, timedelta

    attempt = ExecutionAttempt(
        id=uuid.uuid4(),
        execution_id=domain_exec.id,
        attempt_number=1,
        status=AttemptStatus.FAILED,
        started_at=datetime.now(UTC) - timedelta(minutes=10),
        finished_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    domain_exec._attempts.append(attempt)

    # Save to DB
    repo = SqlAlchemyExecutionRepository(db_session)
    repo.save(domain_exec)
    db_session.commit()

    # Call retry directly (this is what expire_lease does)
    service = ExecutionService()
    retried = service.retry(domain_exec)

    assert retried.status == ExecutionState.QUEUED

    # Wake should NOT be called - the worker is already processing
    mock_wake.assert_not_called()
