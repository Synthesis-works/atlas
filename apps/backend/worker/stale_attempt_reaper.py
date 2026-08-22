"""Stale execution attempt reaper.

If a runner dies mid-execution, attempts remain PENDING/CONTAINER_CREATED/
RUNNING forever and their parent executions stay RUNNING/STARTING, blocking
re-dispatch. This module closes those attempts (FAILED / runner_restarted)
and returns affected non-terminal executions to QUEUED so the outbox sweep
re-dispatches them on the next healthy runner.

Invoked:
- periodically by the outbox sweep loop (rate-limited),
- at runner/CI-driver startup before processing work.
"""

from __future__ import annotations

import uuid as uuid_module
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.orm import Session

from atlas_db.models.execution import AttemptStatus, Execution, ExecutionAttempt, ExecutionStatus
from atlas_db.models.outbox import OutboxMessage

logger = structlog.get_logger(__name__)

# Attempts in these states may be reaped if untouched for the cutoff window.
REAPABLE_STATUSES = (
    AttemptStatus.PENDING,
    AttemptStatus.CONTAINER_CREATED,
    AttemptStatus.RUNNING,
)

# Parent executions eligible for requeue after their attempt was reaped.
REQUEUEABLE_EXECUTION_STATUSES = (
    ExecutionStatus.STARTING,
    ExecutionStatus.RUNNING,
)

TERMINAL_ATTEMPT_STATUSES = (
    AttemptStatus.COMPLETED,
    AttemptStatus.FAILED,
    AttemptStatus.TIMED_OUT,
    AttemptStatus.CANCELLED,
    AttemptStatus.CLEANED,
)

# Invariant: the reap cutoff MUST exceed the maximum possible attempt runtime,
# otherwise legitimately running attempts get reaped mid-flight and their
# executions re-dispatched concurrently (duplicate execution race).
# Outer bounds today: Celery hard kill 61 min (tasks.py time_limit=3660s)
# + DockerExecutor wait grace (+60s). 120 min gives 2x headroom.
MAX_ATTEMPT_RUNTIME_MINUTES = 62
DEFAULT_REAP_AFTER_MINUTES = 120

assert DEFAULT_REAP_AFTER_MINUTES > MAX_ATTEMPT_RUNTIME_MINUTES, (
    "Reaper window must exceed the maximum possible attempt runtime"
)


def reap_stale_attempts(
    db: Session,
    max_age_minutes: int = DEFAULT_REAP_AFTER_MINUTES,
    now: datetime | None = None,
) -> dict[str, int]:
    """Close stale attempts and requeue their parent executions.

    Requeued executions get a fresh ExecutionQueuedEvent outbox row in the same
    transaction so the sweep re-dispatches them (H-4: status flips alone strand
    the execution forever, since only outbox rows trigger processing).

    Returns a summary dict: {"attempts_reaped": n, "executions_requeued": m}.
    Commits only when something changed; safe to call frequently.
    """
    current = now or datetime.now(UTC)
    cutoff = current - timedelta(minutes=max_age_minutes)

    stale_attempts = (
        db.query(ExecutionAttempt)
        .filter(
            ExecutionAttempt.status.in_(REAPABLE_STATUSES),  # type: ignore[attr-defined]
            ExecutionAttempt.updated_at < cutoff,
        )
        .all()
    )

    summary = {"attempts_reaped": 0, "executions_requeued": 0}
    if not stale_attempts:
        return summary

    affected_execution_ids: set[str] = set()
    attempt_trace_ids: dict[str, str] = {}
    for attempt in stale_attempts:
        attempt.status = AttemptStatus.FAILED
        attempt.termination_reason = "runner_restarted"
        attempt.error_message = (
            f"Attempt reaped by stale-attempt reaper after {max_age_minutes} minutes "
            f"without completion."
        )
        attempt.finished_at = current
        summary["attempts_reaped"] += 1
        affected_execution_ids.add(str(attempt.execution_id))
        if attempt.trace_id:
            attempt_trace_ids[str(attempt.execution_id)] = attempt.trace_id

    for execution_id_str in affected_execution_ids:
        execution = db.get(Execution, uuid_module.UUID(execution_id_str))
        if execution is None:
            continue
        if execution.status in REQUEUEABLE_EXECUTION_STATUSES:
            execution.status = ExecutionStatus.QUEUED
            # H-4: only outbox rows trigger processing; a bare status flip to
            # QUEUED would strand the execution forever.
            db.add(
                OutboxMessage(
                    event_id=uuid_module.uuid4(),
                    aggregate_id=execution.id,
                    aggregate_type="Execution",
                    event_type="ExecutionQueuedEvent",
                    event_version=1,
                    schema_version=1,
                    payload={"execution_id": str(execution.id)},
                    trace_context={
                        "trace_id": attempt_trace_ids.get(str(execution.id), ""),
                        "correlation_id": attempt_trace_ids.get(str(execution.id), ""),
                    },
                    occurred_at=current,
                )
            )
            summary["executions_requeued"] += 1

    db.commit()
    logger.info(
        "Reaped stale attempts",
        attempts_reaped=summary["attempts_reaped"],
        executions_requeued=summary["executions_requeued"],
        cutoff=cutoff.isoformat(),
    )
    return summary
