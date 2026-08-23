"""Event-driven resume of agent tasks parked in WAITING_FOR_EXECUTION.

Lifecycle (see docs/AGENT_TASK_LIFECYCLE.md):

    RUNNING -> run_benchmark DISPATCHED (async backend)
            -> WAITING_FOR_EXECUTION        # persisted; Vercel function ends
            -> outbox Execution{Completed,Failed,Cancelled}Event swept on the
               Render worker -> AgentTaskResumeSubscriber -> resume_agent_task
            -> RESUMED (atomic claim) -> EVALUATING -> REPORTING -> COMPLETED

Design invariants:
- The Vercel request NEVER blocks waiting for GitHub Actions.
- Resume is triggered exclusively through the existing transactional-outbox
  sweep infrastructure; there is no parallel polling service.
- Claims are conditional single-row transitions (WAITING_FOR_EXECUTION ->
  RESUMED), so duplicate completion events, outbox redeliveries, and racing
  sweeps are naturally idempotent.
- A task resumes only when ALL of its tracked executions are terminal, and
  the authoritative outcome is read from the executions table, not from the
  event payload.
"""

from __future__ import annotations

import uuid as uuid_module
from datetime import UTC, datetime
from typing import Any, Callable, Optional

import structlog
from sqlalchemy.orm import Session

from atlas_db.models.agent import AgentTaskRecord
from atlas_db.models.execution import Execution

from apps.backend.agent.state import (
    AgentTask,
    AgentTaskStatus,
    ObservationRecord,
)

logger = structlog.get_logger(__name__)

# A crashed/partial resume leaves a row RESUMED; recovery may re-claim it up
# to this many attempts before declaring AGENT_RESUME_FAILED.
MAX_RESUME_ATTEMPTS = 3

# How long a RESUMED row must sit untouched before recovery considers the
# resuming process dead and re-claims it. Must comfortably exceed one
# resume_agent_task invocation (LLM cycles + tool execution).
RESUMED_RECLAIM_MINUTES = 10

OUTCOME_BY_STATUS = {
    "COMPLETED": "COMPLETED",
    "FAILED": "EXECUTION_FAILED",
    "CANCELLED": "EXECUTION_CANCELLED",
    "TIMED_OUT": "EXECUTION_TIMED_OUT",
}

EVENT_TYPES_HANDLED = {
    "ExecutionCompletedEvent",
    "ExecutionFailedEvent",
    "ExecutionCancelledEvent",
}


def _default_provider_factory(task: AgentTask):
    """Build the reasoning provider exactly like the create-task route does."""
    from apps.backend.agent.providers.router import (
        ProviderRouter,
        build_provider_instance,
    )

    model_override = task.model if task.model else None
    primary = build_provider_instance(task.primary_provider, model_override)
    return ProviderRouter(primary=primary) if primary else ProviderRouter()


def find_waiting_tasks_for_execution(
    db: Session, execution_id: uuid_module.UUID
) -> list[AgentTaskRecord]:
    """AgentTaskRecords parked in WAITING_FOR_EXECUTION tracking execution_id."""
    rows = (
        db.query(AgentTaskRecord)
        .filter(AgentTaskRecord.status == AgentTaskStatus.WAITING_FOR_EXECUTION.value)
        .order_by(AgentTaskRecord.created_at.asc())
        .all()
    )
    target = str(execution_id)
    matched: list[AgentTaskRecord] = []
    for row in rows:
        eids = ((row.snapshot or {}).get("execution_ids") or []) if row.snapshot else []
        if target in [str(e) for e in eids]:
            matched.append(row)
    return matched


def _status_label(value: Any) -> str:
    """Normalize SQLAlchemy enum/string statuses to their bare label."""
    return str(getattr(value, "value", value))


def _tracked_execution_statuses(db: Session, execution_ids: list[str]) -> dict[str, str]:
    ids = []
    for raw in execution_ids:
        try:
            ids.append(uuid_module.UUID(str(raw)))
        except ValueError:
            continue
    if not ids:
        return {}
    rows = db.query(Execution.id, Execution.status).filter(Execution.id.in_(ids)).all()
    return {str(row.id): _status_label(row.status) for row in rows}


def _all_tracked_terminal(db: Session, execution_ids: list[str]) -> tuple[bool, dict[str, str]]:
    statuses = _tracked_execution_statuses(db, execution_ids)
    if not statuses:
        return False, statuses
    terminal = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}
    return all(s in terminal for s in statuses.values()), statuses


def claim_waiting_task(db: Session, task_id: uuid_module.UUID) -> Optional[AgentTaskRecord]:
    """Atomically claim a WAITING_FOR_EXECUTION row for resumption.

    Returns the claimed row with status flipped to RESUMED (committed), or
    None when the row is absent or no longer claimable - this is what makes
    duplicate events idempotent.
    """
    record = (
        db.query(AgentTaskRecord)
        .filter(
            AgentTaskRecord.task_id == task_id,
            AgentTaskRecord.status == AgentTaskStatus.WAITING_FOR_EXECUTION.value,
        )
        .first()
    )
    if record is None:
        return None
    snapshot = dict(record.snapshot or {})
    if int(snapshot.get("resume_count") or 0) >= MAX_RESUME_ATTEMPTS:
        logger.warning(
            "agent_task_resume_limit_exceeded",
            task_id=str(task_id),
            resume_count=snapshot.get("resume_count"),
        )
        return None
    record.status = AgentTaskStatus.RESUMED.value
    db.commit()
    return record


def _persist_snapshot(db: Session, record: AgentTaskRecord, task: AgentTask) -> None:
    record.goal = task.goal
    record.status = (
        task.status.value if isinstance(task.status, AgentTaskStatus) else str(task.status)
    )
    record.snapshot = task.model_dump(mode="json")
    db.commit()


def _fail_task(
    db: Session,
    record: AgentTaskRecord,
    task: AgentTask,
    label: str,
    detail: str,
    extra_trace: dict[str, Any] | None = None,
) -> None:
    task.status = AgentTaskStatus.FAILED
    task.completed_at = datetime.now(UTC)
    task.error_detail = f"{label}: {detail}"
    task.add_trace(
        "EXECUTION_TERMINAL_FAILURE" if label.startswith("EXECUTION_") else label.upper(),
        {"label": label, "detail": detail, **(extra_trace or {})},
    )
    _persist_snapshot(db, record, task)


def _resolve_outcome(
    statuses: dict[str, str],
    event_type: str,
    error_message: str | None,
) -> tuple[str, str]:
    """Map authoritative DB execution states to a lifecycle outcome.

    Failure dominates: a mixed set (some COMPLETED, one FAILED) is an
    EXECUTION_FAILED task - never resume into evaluation on a partial run.
    """
    detail = ", ".join(f"{eid}={s}" for eid, s in sorted(statuses.items()))
    if statuses and all(s == "COMPLETED" for s in statuses.values()):
        return "COMPLETED", ""
    for status_value in ("TIMED_OUT", "FAILED", "CANCELLED"):
        if status_value in statuses.values():
            outcome = OUTCOME_BY_STATUS[status_value]
            return outcome, detail or (error_message or "")
    # No tracked executions visible (e.g., event raced ahead of visibility or
    # ids missing): fall back to the event type itself.
    fallback = {
        "ExecutionCompletedEvent": ("COMPLETED", ""),
        "ExecutionFailedEvent": ("EXECUTION_FAILED", error_message or "unknown failure"),
        "ExecutionCancelledEvent": ("EXECUTION_CANCELLED", "cancelled by user"),
    }
    return fallback.get(event_type, ("EXECUTION_FAILED", error_message or "unknown failure"))


def resume_agent_task_core(
    db: Session,
    task_id: uuid_module.UUID,
    *,
    event_type: str = "ExecutionCompletedEvent",
    execution_id: uuid_module.UUID | None = None,
    error_message: str | None = None,
    provider_factory: Optional[Callable[[AgentTask], Any]] = None,
) -> str:
    """Resume a single WAITING agent task from its persisted snapshot.

    Returns one of: NOT_CLAIMED, EXECUTION_FAILED, EXECUTION_CANCELLED,
    EXECUTION_TIMED_OUT, COMPLETED, FAILED (agent loop failed after resume).
    Raises on infrastructure errors so the Celery layer can retry.
    """
    record = claim_waiting_task(db, task_id)
    if record is None:
        logger.info("agent_task_resume_skipped_not_claimable", task_id=str(task_id))
        return "NOT_CLAIMED"

    task = AgentTask.model_validate(dict(record.snapshot or {}))
    task.status = AgentTaskStatus.RESUMED
    task.resume_count += 1
    task.waiting_since = None
    task.consecutive_non_progress_steps = 0
    task.add_trace(
        "AGENT_TASK_RESUMED",
        {
            "event_type": event_type,
            "execution_id": str(execution_id) if execution_id else None,
            "resume_count": task.resume_count,
        },
    )

    statuses = _tracked_execution_statuses(db, task.execution_ids)
    outcome, detail = _resolve_outcome(statuses, event_type, error_message)

    if outcome != "COMPLETED":
        _fail_task(db, record, task, outcome, detail)
        return outcome

    # Synthesize terminal observations so the resumed context reflects the
    # completed runs even when the original process died before recording them.
    target_ids = [str(execution_id)] if execution_id is not None else list(task.execution_ids)
    for eid in target_ids:
        already_observed = any(
            o.tool_name == "get_run_status"
            and isinstance(o.output, dict)
            and str(o.output.get("execution_id")) == str(eid)
            and o.output.get("status") == "COMPLETED"
            for o in task.observations
        )
        if not already_observed:
            task.observations.append(
                ObservationRecord(
                    call_id=uuid_module.uuid4().hex,
                    tool_name="get_run_status",
                    success=True,
                    output={
                        "execution_id": str(eid),
                        "status": "COMPLETED",
                        "progress": "100%",
                        "resumed": True,
                    },
                )
            )

    factory = provider_factory or _default_provider_factory
    from apps.backend.agent.agent import AtlasAgent

    agent = AtlasAgent(provider=factory(task))
    task = agent.run_task(task, db)

    _persist_snapshot(db, record, task)
    return "COMPLETED" if task.status == AgentTaskStatus.COMPLETED else str(task.status.value)


def handle_terminal_execution_event(
    db: Session,
    execution_id: uuid_module.UUID,
    event_type: str,
    error_message: str | None = None,
    provider_factory: Optional[Callable[[AgentTask], Any]] = None,
) -> list[str]:
    """Resume every WAITING task that tracks this execution and is fully done.

    Tasks with other still-in-flight executions stay WAITING; their own
    terminal events (or the stale-WAITING sweep) will resume them later.
    """
    outcomes: list[str] = []
    for record in find_waiting_tasks_for_execution(db, execution_id):
        snapshot = record.snapshot or {}
        eids = [str(e) for e in (snapshot.get("execution_ids") or [])]
        all_terminal, statuses = _all_tracked_terminal(db, eids)
        if not all_terminal:
            logger.info(
                "agent_task_resume_deferred_inflight_siblings",
                task_id=str(record.task_id),
                execution_id=str(execution_id),
                statuses=statuses,
            )
            continue
        outcome = resume_agent_task_core(
            db,
            record.task_id,
            event_type=event_type,
            execution_id=execution_id,
            error_message=error_message,
            provider_factory=provider_factory,
        )
        outcomes.append(outcome)
    return outcomes


def _aware(value: datetime | None) -> datetime | None:
    """sqlite returns naive UTC datetimes; normalize for arithmetic."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def recover_stale_waiting_tasks(
    db: Session,
    now: datetime | None = None,
    provider_factory: Optional[Callable[[AgentTask], Any]] = None,
) -> dict[str, int]:
    """Sweep-time safety net for WAITING tasks whose events were lost.

    - All tracked executions terminal (event lost / race at persist time):
      resume normally via the standard claim path.
    - Still non-terminal past the wait deadline: force-fail with
      AGENT_RESUME_TIMEOUT so tasks never strand forever.
    - RESUMED rows older than RESUMED_RECLAIM_MINUTES (crashed resume):
      re-claim up to MAX_RESUME_ATTEMPTS, then fail AGENT_RESUME_FAILED.
    - PENDING/EXECUTING rows untouched far past creation (pre-park orphans,
      e.g. serverless kills before any checkpoint persist): force-fail so
      they stop rendering as live tasks.

    Mirrors the role stale_attempt_reaper plays for execution attempts.
    """
    current = now or datetime.now(UTC)
    summary = {"resumed": 0, "timed_out": 0, "resume_failed": 0, "reaped_orphans": 0}

    rows = (
        db.query(AgentTaskRecord)
        .filter(
            AgentTaskRecord.status.in_(
                [
                    AgentTaskStatus.PENDING.value,
                    AgentTaskStatus.EXECUTING.value,
                    AgentTaskStatus.WAITING_FOR_EXECUTION.value,
                    AgentTaskStatus.RESUMED.value,
                ]
            )
        )
        .order_by(AgentTaskRecord.created_at.asc())
        .all()
    )

    deadline_seconds = 480
    try:
        from apps.backend.config import settings

        deadline_seconds = int(settings.agent_execution_wait_deadline_seconds)
    except Exception:  # pragma: no cover - config always available in practice
        pass

    for record in rows:
        snapshot = dict(record.snapshot or {})
        status_value = record.status
        updated_at = _aware(record.updated_at)
        age_minutes = (current - updated_at).total_seconds() / 60.0 if updated_at else float("inf")

        if status_value in (AgentTaskStatus.PENDING.value, AgentTaskStatus.EXECUTING.value):
            # Orphan guard: a live task persists checkpoints as it progresses,
            # so a row stuck in PENDING/EXECUTING well past the wait window
            # means its process died before parking. There is no reliable
            # execution mapping to resume from; reap it.
            if age_minutes > max(deadline_seconds / 60.0, 60.0):
                task = AgentTask.model_validate(snapshot)
                _fail_task(
                    db,
                    record,
                    task,
                    "AGENT_RESUME_TIMEOUT",
                    f"orphaned {status_value} task reaped after "
                    f"{age_minutes:.0f}m without a park or completion",
                )
                summary["reaped_orphans"] += 1
            continue

        if status_value == AgentTaskStatus.RESUMED.value:
            if age_minutes < RESUMED_RECLAIM_MINUTES:
                continue
            if int(snapshot.get("resume_count") or 0) >= MAX_RESUME_ATTEMPTS:
                task = AgentTask.model_validate(snapshot)
                _fail_task(
                    db,
                    record,
                    task,
                    "AGENT_RESUME_FAILED",
                    f"resume attempted {task.resume_count}x without completion",
                )
                summary["resume_failed"] += 1
            else:
                task = AgentTask.model_validate(snapshot)
                task.waiting_since = task.waiting_since or current
                record.status = AgentTaskStatus.WAITING_FOR_EXECUTION.value
                record.snapshot = task.model_dump(mode="json")
                db.commit()
            continue

        eids = [str(e) for e in (snapshot.get("execution_ids") or [])]
        all_terminal, statuses = _all_tracked_terminal(db, eids)
        if all_terminal:
            outcome = resume_agent_task_core(
                db,
                record.task_id,
                event_type="ExecutionCompletedEvent",
                provider_factory=provider_factory,
            )
            if outcome != "NOT_CLAIMED":
                summary["resumed"] += 1
            continue

        waited_minutes = None
        waiting_since = _aware(
            datetime.fromisoformat(str(snapshot.get("waiting_since")))
            if snapshot.get("waiting_since")
            else None
        )
        if waiting_since:
            waited_minutes = (current - waiting_since).total_seconds() / 60.0

        overdue = waited_minutes is not None and (waited_minutes * 60.0 > deadline_seconds)
        if overdue or age_minutes > max(deadline_seconds / 60.0, 60.0):
            task = AgentTask.model_validate(snapshot)
            _fail_task(
                db,
                record,
                task,
                "AGENT_RESUME_TIMEOUT",
                f"no terminal execution event within the wait window; statuses={statuses}",
            )
            summary["timed_out"] += 1

    return summary


class AgentTaskResumeSubscriber:
    """Outbox subscriber: enqueues agent-task resumes for terminal events.

    Registered in worker.tasks.outbox_sweep_task alongside the evaluation and
    snapshot subscribers. Enqueue-only here; all DB work happens inside the
    resume_agent_task Celery task so eager mode (Render/local) executes it
    inline and brokered mode queues it safely.
    """

    def handle(self, event: Any) -> None:
        event_type_name = type(event).__name__
        if event_type_name not in EVENT_TYPES_HANDLED:
            return
        execution_id = getattr(event, "aggregate_id", None) or getattr(event, "execution_id", None)
        if execution_id is None:
            return
        error_message = getattr(event, "error_message", None)
        logger.info(
            "agent_task_resume_enqueued",
            execution_id=str(execution_id),
            event_type=event_type_name,
        )
        from apps.backend.worker.agent_resume import resume_agent_task

        resume_agent_task.delay(str(execution_id), event_type_name, error_message)


from apps.backend.worker.celery_app import celery_app  # noqa: E402


@celery_app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=1500,
    time_limit=1560,
)
def resume_agent_task(
    self,
    execution_id_str: str,
    event_type: str = "ExecutionCompletedEvent",
    error_message: str | None = None,
):
    """Resume WAITING agent tasks after an execution reaches a terminal state.

    Idempotent: only tasks still claimable (WAITING_FOR_EXECUTION) proceed;
    duplicate events and redeliveries no-op via the conditional claim.
    """
    from atlas_db.core.session import SessionLocal

    try:
        execution_id = uuid_module.UUID(str(execution_id_str))
    except ValueError:
        logger.error("agent_task_resume_invalid_execution_id", raw=execution_id_str)
        return

    with SessionLocal() as db:
        outcomes = handle_terminal_execution_event(db, execution_id, event_type, error_message)
    if outcomes:
        logger.info(
            "agent_task_resume_finished",
            execution_id=execution_id_str,
            event_type=event_type,
            outcomes=outcomes,
        )
