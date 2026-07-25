import uuid
from unittest.mock import MagicMock

import pytest

from packages.execution_engine.application.scheduler_service import SchedulerService
from packages.execution_engine.domain.events import (
    ExecutionRetryEvent,
    LeaseExpiredEvent,
)
from packages.execution_engine.domain.models import ExecutionState


@pytest.fixture
def mock_domain_service():
    service = MagicMock()
    return service


@pytest.fixture
def mock_execution_repo():
    repo = MagicMock()
    return repo


@pytest.fixture
def scheduler(mock_domain_service, mock_execution_repo):
    return SchedulerService(mock_domain_service, mock_execution_repo)


def test_scheduler_sweeps_expired_leases(
    scheduler, mock_execution_repo, mock_domain_service
):
    mock_execution = MagicMock()
    mock_execution.id = uuid.uuid4()
    mock_execution.status = ExecutionState.RETRYING
    mock_execution.pull_events.return_value = [
        LeaseExpiredEvent(
            timestamp=MagicMock(),
            execution_id=mock_execution.id,
            attempt_id=uuid.uuid4(),
            worker_id=uuid.uuid4(),
        ),
        ExecutionRetryEvent(
            timestamp=MagicMock(),
            execution_id=mock_execution.id,
            attempt_id=uuid.uuid4(),
            error_message="Lease expired",
        ),
    ]

    mock_execution_repo.find_expired_active_attempts.return_value = [mock_execution]

    # Run sweep
    count = scheduler.sweep_expired_leases()

    assert count == 1
    mock_execution_repo.find_expired_active_attempts.assert_called_once()
    mock_domain_service.expire_lease.assert_called_once_with(mock_execution)
    mock_execution_repo.save.assert_called_once_with(mock_execution)


def test_scheduler_best_effort_batching(scheduler, mock_execution_repo, mock_domain_service):
    # Setup 3 executions. The second one will fail to process.
    exec_1 = MagicMock()
    exec_2 = MagicMock()
    exec_3 = MagicMock()

    mock_execution_repo.find_expired_active_attempts.return_value = [exec_1, exec_2, exec_3]

    def side_effect(execution):
        if execution == exec_2:
            raise ValueError("Simulated domain crash")
        return execution

    mock_domain_service.expire_lease.side_effect = side_effect

    count = scheduler.sweep_expired_leases()

    assert count == 2  # 1 and 3 processed
    assert mock_execution_repo.save.call_count == 2
    mock_execution_repo.save.assert_any_call(exec_1)
    mock_execution_repo.save.assert_any_call(exec_3)


def test_scheduler_save_failure_does_not_rollback_batch(
    scheduler, mock_execution_repo
):
    exec_1 = MagicMock()
    exec_2 = MagicMock()

    mock_execution_repo.find_expired_active_attempts.return_value = [exec_1, exec_2]
    mock_execution_repo.save.side_effect = [Exception("Simulated save failure"), None]

    count = scheduler.sweep_expired_leases()

    # Save failure for exec_1 is caught and logged, exec_2 succeeds
    assert count == 1
    assert mock_execution_repo.save.call_count == 2
