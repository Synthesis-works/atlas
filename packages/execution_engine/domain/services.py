from typing import Optional
import uuid

from packages.execution_engine.domain.clock import Clock
from packages.execution_engine.domain.models import (
    Execution, ExecutionState, AttemptStatus
)
from packages.execution_engine.domain.events import (
    ExecutionQueuedEvent, ExecutionStartedEvent, 
    ExecutionCancelledEvent, ExecutionFailedEvent, ExecutionCompletedEvent,
    ExecutionRetryEvent, LeaseExpiredEvent
)
from packages.execution_engine.domain.exceptions import (
    InvalidStateTransitionError,
    InvariantViolationError,
    ImmutableExecutionError,
    LeaseOwnershipError,
    RetryLimitExceededError
)

class ExecutionService:
    """
    Pure domain service for Execution.
    No SQL, No HTTP, No external I/O.
    """
    def __init__(self, clock: Clock = Clock()):
        self.clock = clock

    def _assert_not_terminal(self, execution: Execution):
        if execution.is_terminal():
            raise ImmutableExecutionError(f"Execution {execution.id} is in terminal state {execution.status.name} and cannot be modified.")

    def create_execution(self, execution_id: uuid.UUID, benchmark_version_id: uuid.UUID, submitted_by: uuid.UUID) -> Execution:
        execution = Execution(
            id=execution_id,
            benchmark_version_id=benchmark_version_id,
            created_by=submitted_by,
            status=ExecutionState.QUEUED,
            created_at=self.clock.now(),
            updated_at=self.clock.now()
        )
        event = ExecutionQueuedEvent(
            timestamp=self.clock.now(),
            execution_id=execution.id,
            benchmark_version_id=benchmark_version_id,
            submitted_by=submitted_by
        )
        execution.record_event(event)
        return execution

    def acquire_lease(self, execution: Execution, worker_id: uuid.UUID, lease_duration_seconds: int = 300) -> Execution:
        self._assert_not_terminal(execution)
        
        if execution.status != ExecutionState.QUEUED:
            raise InvalidStateTransitionError(f"Cannot acquire lease from state {execution.status.name}")

        if execution.has_active_lease(self.clock):
            raise InvariantViolationError("Execution already has an active lease.")

        # This inherently validates "only one active attempt" and sets up lease
        attempt = execution.begin_attempt(worker_id, self.clock, lease_duration_seconds)
        
        execution.status = ExecutionState.SCHEDULED
        execution.updated_at = self.clock.now()

        event = ExecutionStartedEvent(
            timestamp=self.clock.now(),
            execution_id=execution.id,
            attempt_id=attempt.id,
            worker_id=worker_id
        )
        execution.record_event(event)
        return execution

    def start_execution(self, execution: Execution, worker_id: uuid.UUID) -> Execution:
        self._assert_not_terminal(execution)
        
        if execution.status != ExecutionState.SCHEDULED:
            raise InvalidStateTransitionError(f"Cannot transition to STARTING from {execution.status.name}")
            
        attempt = execution.current_attempt
        if not attempt or not attempt.lease or attempt.lease.worker_id != worker_id:
            raise LeaseOwnershipError("Worker does not hold the active lease for this execution.")
            
        execution.status = ExecutionState.STARTING
        execution.updated_at = self.clock.now()
        return execution

    def run_execution(self, execution: Execution, worker_id: uuid.UUID) -> Execution:
        self._assert_not_terminal(execution)
        
        if execution.status != ExecutionState.STARTING:
            raise InvalidStateTransitionError(f"Cannot transition to RUNNING from {execution.status.name}")
            
        attempt = execution.current_attempt
        if not attempt or not attempt.lease or attempt.lease.worker_id != worker_id:
            raise LeaseOwnershipError("Worker does not hold the active lease for this execution.")
            
        execution.status = ExecutionState.RUNNING
        execution.updated_at = self.clock.now()
        return execution

    def cancel(self, execution: Execution) -> Execution:
        if execution.is_terminal():
            raise ImmutableExecutionError("Cannot cancel a terminal execution.")
            
        execution.status = ExecutionState.CANCELLING
        execution.updated_at = self.clock.now()
        
        execution.cancel_attempt(self.clock)
        attempt = execution.current_attempt
            
        event = ExecutionCancelledEvent(
            timestamp=self.clock.now(),
            execution_id=execution.id,
            attempt_id=attempt.id if attempt else None
        )
        
        # If it was queued and never had an attempt, we can just move to CANCELLED immediately
        if not attempt:
            execution.status = ExecutionState.CANCELLED
            
        execution.record_event(event)
        return execution
        
    def complete_cancellation(self, execution: Execution) -> Execution:
        if execution.status != ExecutionState.CANCELLING:
            raise InvalidStateTransitionError("Can only complete cancellation from CANCELLING state.")
            
        execution.status = ExecutionState.CANCELLED
        execution.updated_at = self.clock.now()
        return execution

    def complete(self, execution: Execution, worker_id: uuid.UUID) -> Execution:
        # Idempotency check
        if execution.status == ExecutionState.COMPLETED:
            return execution
            
        if execution.status not in [ExecutionState.RUNNING, ExecutionState.EVALUATING]:
            raise InvalidStateTransitionError(f"Cannot complete execution from {execution.status.name}")

        attempt = execution.current_attempt
        if not attempt or not attempt.lease or attempt.lease.worker_id != worker_id:
            raise LeaseOwnershipError("Worker does not hold the active lease.")

        execution.status = ExecutionState.COMPLETED
        execution.updated_at = self.clock.now()
        
        execution.finish_attempt(self.clock)
        
        event = ExecutionCompletedEvent(
            timestamp=self.clock.now(),
            execution_id=execution.id,
            attempt_id=attempt.id
        )
        execution.record_event(event)
        return execution

    def fail(self, execution: Execution, error_message: str, worker_id: Optional[uuid.UUID] = None) -> Execution:
        # Idempotency check
        if execution.status == ExecutionState.FAILED:
            return execution
            
        if execution.is_terminal():
            raise ImmutableExecutionError("Cannot fail a terminal execution.")

        attempt = execution.current_attempt
        
        # If worker_id is provided, verify ownership (unless it's a sweeper forcing a failure due to expiry)
        if attempt and attempt.lease and worker_id and attempt.lease.worker_id != worker_id:
            raise LeaseOwnershipError("Worker does not hold the active lease.")

        execution.fail_attempt(error_message, self.clock)

        will_retry = False
        if attempt and attempt.attempt_number < execution.max_retries:
            will_retry = True

        if will_retry:
            execution.status = ExecutionState.RETRYING
            execution.updated_at = self.clock.now()
            execution.record_event(ExecutionRetryEvent(
                timestamp=self.clock.now(),
                execution_id=execution.id,
                attempt_id=attempt.id,
                error_message=error_message
            ))
        else:
            execution.status = ExecutionState.FAILED
            execution.updated_at = self.clock.now()
            execution.record_event(ExecutionFailedEvent(
                timestamp=self.clock.now(),
                execution_id=execution.id,
                attempt_id=attempt.id if attempt else None,
                error_message=error_message,
                will_retry=False
            ))
            
        return execution

    def retry(self, execution: Execution) -> Execution:
        if execution.status != ExecutionState.RETRYING:
            raise InvalidStateTransitionError(f"Cannot transition to QUEUED from {execution.status.name}")
            
        # Re-enforce invariant: Cannot retry if attempt limit is reached 
        if execution.current_attempt and execution.current_attempt.attempt_number >= execution.max_retries:
            raise RetryLimitExceededError("Cannot retry: max retries exceeded.")
            
        execution.status = ExecutionState.QUEUED
        execution.updated_at = self.clock.now()
        
        event = ExecutionQueuedEvent(
            timestamp=self.clock.now(),
            execution_id=execution.id,
            benchmark_version_id=execution.benchmark_version_id,
            submitted_by=execution.created_by
        )
        execution.record_event(event)
        return execution

    def expire_lease(self, execution: Execution) -> Execution:
        """
        Handles an expired lease. Checks that the lease is actually expired,
        emits LeaseExpiredEvent, and delegates to fail() which handles the
        transition to RETRYING or FAILED natively.
        """
        attempt = execution.current_attempt
        if not attempt or not attempt.lease:
            raise InvalidStateTransitionError("Cannot expire lease: No active lease exists.")
            
        if attempt.lease.expires_at > self.clock.now():
            raise InvariantViolationError("Cannot expire lease: Lease is still valid.")
            
        worker_id = attempt.lease.worker_id

        # 1. Emit LeaseExpiredEvent
        execution.record_event(LeaseExpiredEvent(
            timestamp=self.clock.now(),
            execution_id=execution.id,
            attempt_id=attempt.id,
            worker_id=worker_id
        ))

        # 2. Let domain handle retry exhaustion
        # This will fail the attempt and emit either ExecutionRetryEvent or ExecutionFailedEvent
        self.fail(execution, error_message="Lease expired", worker_id=worker_id)
        
        # 3. If the domain decided to retry, immediately requeue it natively.
        if execution.status == ExecutionState.RETRYING:
            self.retry(execution)
            
        return execution
