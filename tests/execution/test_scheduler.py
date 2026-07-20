import pytest
from unittest.mock import MagicMock
import uuid

from packages.execution_engine.application.scheduler_service import SchedulerService
from packages.execution_engine.domain.models import ExecutionState
from packages.execution_engine.domain.events import LeaseExpiredEvent, ExecutionRetryEvent, ExecutionFailedEvent

@pytest.fixture
def mock_domain_service():
    service = MagicMock()
    return service

@pytest.fixture
def mock_execution_repo():
    repo = MagicMock()
    return repo

@pytest.fixture
def mock_event_publisher():
    publisher = MagicMock()
    return publisher

@pytest.fixture
def scheduler(mock_domain_service, mock_execution_repo, mock_event_publisher):
    return SchedulerService(mock_domain_service, mock_execution_repo, mock_event_publisher)

def test_scheduler_sweeps_expired_leases(scheduler, mock_execution_repo, mock_domain_service, mock_event_publisher):
    mock_execution = MagicMock()
    mock_execution.id = uuid.uuid4()
    mock_execution.status = ExecutionState.RETRYING
    mock_execution.pull_events.return_value = [
        LeaseExpiredEvent(timestamp=MagicMock(), execution_id=mock_execution.id, attempt_id=uuid.uuid4(), worker_id=uuid.uuid4()),
        ExecutionRetryEvent(timestamp=MagicMock(), execution_id=mock_execution.id, attempt_id=uuid.uuid4(), error_message="Lease expired")
    ]
    
    mock_execution_repo.find_expired_active_attempts.return_value = [mock_execution]
    
    # Run sweep
    count = scheduler.sweep_expired_leases()
    
    assert count == 1
    mock_execution_repo.find_expired_active_attempts.assert_called_once()
    mock_domain_service.expire_lease.assert_called_once_with(mock_execution)
    mock_execution_repo.save.assert_called_once_with(mock_execution)
    mock_event_publisher.publish.assert_called_once()
    events_published = mock_event_publisher.publish.call_args[0][0]
    assert len(events_published) == 2
    assert isinstance(events_published[0], LeaseExpiredEvent)
    assert isinstance(events_published[1], ExecutionRetryEvent)

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
    
    assert count == 2 # 1 and 3 processed
    assert mock_execution_repo.save.call_count == 2
    mock_execution_repo.save.assert_any_call(exec_1)
    mock_execution_repo.save.assert_any_call(exec_3)

def test_scheduler_publish_failure_does_not_rollback_batch(scheduler, mock_execution_repo, mock_event_publisher):
    exec_1 = MagicMock()
    
    mock_execution_repo.find_expired_active_attempts.return_value = [exec_1]
    mock_event_publisher.publish.side_effect = Exception("Simulated publish failure")
    
    count = scheduler.sweep_expired_leases()
    
    # Event publish failure is caught and logged, the sweep is considered successful in terms of persistence
    assert count == 1
    mock_execution_repo.save.assert_called_once_with(exec_1)
