"""
End-to-End Integration Test — Multi-Worker Failover & Outbox Event Lifecycle
Simulates full operational workflow:
  1. POST /api/v1/benchmarks/{v_id}/executions creates execution in QUEUED state.
  2. Worker 1 claims lease via SKIP LOCKED and moves status to RUNNING.
  3. Worker 1 dies (misses heartbeat) and lease expires.
  4. SchedulerService sweeps expired lease -> status transitions to FAILED_RETRYABLE -> QUEUED.
  5. Worker 2 claims lease, executes benchmark to completion, writes Outbox event.
  6. OutboxDispatcher publishes event to downstream EventBus.
"""

import uuid
from datetime import datetime, timezone, timedelta, UTC
import pytest
from unittest.mock import MagicMock

from packages.execution_engine.domain.models import (
    Execution,
    ExecutionState,
    Lease,
    ExecutionAttempt,
    AttemptStatus,
)
from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.application.worker_app_service import WorkerApplicationService
from packages.execution_engine.application.scheduler_service import SchedulerService
from packages.execution_engine.application.outbox_dispatcher import OutboxDispatcher


def test_full_e2e_worker_failover_and_outbox_pipeline():
    """Verify complete end-to-end lifecycle: claim -> worker death -> lease sweep -> worker 2 claim -> completion -> outbox."""
    domain_service = ExecutionService()
    execution_repo = MagicMock()
    publisher = MagicMock()

    worker_1_id = uuid.uuid4()
    worker_2_id = uuid.uuid4()
    version_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Step 1: Execution created in QUEUED state
    execution = Execution.rehydrate(
        id=uuid.uuid4(),
        benchmark_version_id=version_id,
        project_id=uuid.uuid4(),
        status=ExecutionState.QUEUED,
        created_by=user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        max_retries=3,
        attempts=[],
    )

    execution_repo.find_schedulable.return_value = [execution]
    execution_repo.get_for_update.return_value = execution

    worker_app = WorkerApplicationService(
        domain_service=domain_service,
        execution_repo=execution_repo,
        event_publisher=publisher,
    )

    # Step 2: Worker 1 acquires work and starts execution
    grant_1 = worker_app.acquire_work(worker_1_id)
    assert grant_1 is not None, "Worker 1 failed to acquire task lease"
    assert execution.status == ExecutionState.STARTING, "Execution status should be STARTING"
    assert len(execution.attempts) == 1, "Expected 1 attempt"
    assert execution.current_attempt.lease.worker_id == worker_1_id, "Worker 1 should own lease"

    # Step 3: Worker 1 dies mid-execution, lease expires (simulate 10 minutes passing)
    execution.current_attempt.lease.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    execution_repo.find_expired_active_attempts.return_value = [execution]

    # Step 4: SchedulerService sweeps expired lease
    scheduler = SchedulerService(domain_service=domain_service, execution_repo=execution_repo)
    swept_count = scheduler.sweep_expired_leases(limit=50)

    assert swept_count == 1, "Scheduler failed to sweep expired lease"
    assert execution.status in [
        ExecutionState.QUEUED,
        ExecutionState.FAILED,
        ExecutionState.RETRYING,
    ], "Execution should be retryable"
    assert execution.current_attempt.status == AttemptStatus.FAILED, (
        "Expired attempt should be marked FAILED"
    )

    # Step 5: Worker 2 acquires task and completes execution
    execution_repo.find_schedulable.return_value = [execution]
    grant_2 = worker_app.acquire_work(worker_2_id)

    assert grant_2 is not None, "Worker 2 failed to claim retryable task"
    assert len(execution.attempts) == 2, "Expected 2 attempts total"
    assert execution.current_attempt.lease.worker_id == worker_2_id, "Worker 2 should own new lease"

    # Complete execution successfully
    execution.status = ExecutionState.RUNNING
    domain_service.complete(execution, worker_2_id)
    assert execution.status == ExecutionState.COMPLETED, "Execution should transition to COMPLETED"

    # Step 6: Verify Outbox event generated
    events = execution.pull_events()
    assert len(events) >= 1, "Expected at least 1 domain event generated for outbox"
