import uuid
from datetime import UTC, datetime, timedelta

import pytest

from packages.execution_engine.domain.clock import TestClock
from packages.execution_engine.domain.events import (
    ExecutionCompletedEvent,
    ExecutionFailedEvent,
    ExecutionQueuedEvent,
    ExecutionRetryEvent,
    ExecutionStartedEvent,
)
from packages.execution_engine.domain.exceptions import (
    ImmutableExecutionError,
    InvalidStateTransitionError,
    InvariantViolationError,
    LeaseOwnershipError,
)
from packages.execution_engine.domain.models import (
    AttemptStatus,
    ExecutionState,
)
from packages.execution_engine.domain.services import ExecutionService


@pytest.fixture
def test_clock():
    return TestClock(datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC))


@pytest.fixture
def service(test_clock):
    return ExecutionService(clock=test_clock)


def test_create_execution(service):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)

    assert execution.id == exec_id
    assert execution.status == ExecutionState.QUEUED
    events = execution.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], ExecutionQueuedEvent)
    assert not execution.has_active_lease(service.clock)


def test_acquire_lease(service, test_clock):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    execution.pull_events()

    worker_id = uuid.uuid4()
    updated_exec = service.acquire_lease(execution, worker_id)

    assert updated_exec.status == ExecutionState.SCHEDULED
    assert len(updated_exec.attempts) == 1
    assert updated_exec.current_attempt.attempt_number == 1
    assert updated_exec.current_attempt.lease.worker_id == worker_id
    assert updated_exec.has_active_lease(service.clock)
    events = updated_exec.pull_events()
    assert isinstance(events[0], ExecutionStartedEvent)


def test_double_acquire_lease_fails(service):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)

    with pytest.raises(InvalidStateTransitionError):
        service.acquire_lease(execution, uuid.uuid4())


def test_start_and_run(service):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)

    updated_exec = service.start_execution(execution, worker_id)
    assert updated_exec.status == ExecutionState.STARTING

    updated_exec = service.run_execution(execution, worker_id)
    assert updated_exec.status == ExecutionState.RUNNING


def test_wrong_worker_fails_invariants(service):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)

    wrong_worker = uuid.uuid4()
    with pytest.raises(LeaseOwnershipError):
        service.start_execution(execution, wrong_worker)


def test_complete_execution(service):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)
    service.start_execution(execution, worker_id)
    service.run_execution(execution, worker_id)
    execution.pull_events()

    updated_exec = service.complete(execution, worker_id)
    assert updated_exec.status == ExecutionState.COMPLETED
    assert updated_exec.current_attempt.status == AttemptStatus.SUCCESS
    events = updated_exec.pull_events()
    assert isinstance(events[0], ExecutionCompletedEvent)


def test_duplicate_complete_is_idempotent(service):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)
    service.start_execution(execution, worker_id)
    service.run_execution(execution, worker_id)

    service.complete(execution, worker_id)
    execution.pull_events()
    # Second time should just return execution, no events, no errors
    updated_exec = service.complete(execution, worker_id)
    events = updated_exec.pull_events()
    assert len(events) == 0


def test_fail_and_retry(service, test_clock):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)
    service.start_execution(execution, worker_id)
    execution.pull_events()

    # Fail 1
    updated_exec = service.fail(execution, "OOM", worker_id)
    assert updated_exec.status == ExecutionState.RETRYING
    events = updated_exec.pull_events()
    assert isinstance(events[0], ExecutionRetryEvent)

    # Retry
    service.retry(execution)
    assert execution.status == ExecutionState.QUEUED

    # Attempt 2
    service.acquire_lease(execution, worker_id)
    service.fail(execution, "OOM", worker_id)
    service.retry(execution)

    # Attempt 3
    service.acquire_lease(execution, worker_id)
    updated_exec = service.fail(execution, "Terminal", worker_id)

    # Should be terminal FAILED since max_retries = 3
    assert updated_exec.status == ExecutionState.FAILED
    events = updated_exec.pull_events()
    assert any(isinstance(e, ExecutionFailedEvent) for e in events)


def test_immutable_terminal_states(service):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)
    service.start_execution(execution, worker_id)
    service.run_execution(execution, worker_id)
    service.complete(execution, worker_id)

    with pytest.raises(ImmutableExecutionError):
        service.cancel(execution)

    with pytest.raises(ImmutableExecutionError):
        service.fail(execution, "Should not happen", worker_id)


def test_expire_lease_exhausts_retries(service, test_clock):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)

    # Attempt 1
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)
    execution.pull_events()  # clear queued and started

    # Fast forward clock to expire lease
    test_clock.set_time(test_clock.now() + timedelta(seconds=301))

    updated_exec = service.expire_lease(execution)

    # Should automatically transition to queued after a retry
    assert updated_exec.status == ExecutionState.QUEUED
    events = updated_exec.pull_events()
    assert len(events) == 3
    # Validate causal order
    from packages.execution_engine.domain.events import ExecutionRetryEvent, LeaseExpiredEvent

    assert isinstance(events[0], LeaseExpiredEvent)
    assert isinstance(events[1], ExecutionRetryEvent)
    assert isinstance(events[2], ExecutionQueuedEvent)

    # Exhaust retries
    # Attempt 2
    service.acquire_lease(execution, worker_id)
    test_clock.set_time(test_clock.now() + timedelta(seconds=301))
    service.expire_lease(execution)

    # Attempt 3 (Max retries = 3)
    service.acquire_lease(execution, worker_id)
    test_clock.set_time(test_clock.now() + timedelta(seconds=301))
    execution.pull_events()

    updated_exec = service.expire_lease(execution)

    # Should now be terminal FAILED, no more retries
    assert updated_exec.status == ExecutionState.FAILED
    events = updated_exec.pull_events()
    assert len(events) == 2
    from packages.execution_engine.domain.events import ExecutionFailedEvent

    assert isinstance(events[0], LeaseExpiredEvent)
    assert isinstance(events[1], ExecutionFailedEvent)


def test_expire_lease_unexpired_fails(service, test_clock):
    exec_id, bv_id, user_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    execution = service.create_execution(exec_id, bv_id, user_id)
    worker_id = uuid.uuid4()
    service.acquire_lease(execution, worker_id)

    with pytest.raises(InvariantViolationError, match="Lease is still valid"):
        service.expire_lease(execution)
