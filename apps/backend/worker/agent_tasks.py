"""Durable Celery execution of Atlas Agent reasoning loops.

Why this exists
---------------
The create/clarify/approve/run-again routes historically ran the agent loop on
the FastAPI thread via ``BackgroundTasks``. On Vercel serverless, the instance
is frozen once the HTTP response is sent, which could strand a loop mid-step
(status stuck in EXECUTING) or lose the task entirely across instances. This
module mirrors ``agent_resume.py``: it loads the persisted ``AgentTaskRecord``
snapshot, registers the live task in the process-local ``_agent_tasks_db``
(which the tools use to attach execution/report lineage), runs
``AtlasAgent.run_task``, and checkpoints the snapshot back with ownership +
liveness metadata.

Lifecycle (dual-mode)
---------------------
``AGENT_TASKS_CELERY_EXECUTION=false`` (default; local dev + unit tests):
    the router keeps the existing in-process background path.
``AGENT_TASKS_CELERY_EXECUTION=true`` (prod recommendation):
    the router writes an ``AgentRunRequestedEvent`` transactional-outbox row
    (never enqueues to Redis directly - the serverless API has no broker),
    and this module's worker-side ``AgentRunSubscriber`` - fired by the outbox
    sweep - enqueues ``run_agent_task`` on the durable Render worker. The
    outbox-driven resume flow in ``agent_resume.py`` already runs on Celery in
    both modes, so the two halves of the lifecycle are finally co-located.

Ownership & liveness
--------------------
The task records ``instance_id`` (worker node id) and refreshes
``heartbeat_at`` on every checkpoint. ``recover_stale_waiting_tasks`` can use
those columns to distinguish a live loop from a frozen process when reclaiming
orphaned rows.
"""

from __future__ import annotations

import uuid as uuid_module
from datetime import UTC, datetime
from typing import Any, Optional

import structlog
from sqlalchemy.orm import Session

from atlas_db.models.agent import AgentTaskRecord

from apps.backend.agent.state import AgentTask, AgentTaskStatus

logger = structlog.get_logger(__name__)


class AgentRunSubscriber:
    """Outbox subscriber: enqueues agent-task runs on the worker side.

    Registered in ``worker.tasks.outbox_sweep_task`` alongside the execution,
    evaluation, snapshot and resume subscribers. Enqueue-only here; all DB work
    happens inside ``run_agent_task`` so eager mode executes it inline and
    brokered mode queues it safely on the worker's own broker.
    """

    def handle(self, event: Any) -> None:
        if type(event).__name__ != "AgentRunRequestedEvent":
            return
        task_id = getattr(event, "task_id", None)
        if task_id is None:
            return
        provider_type = getattr(event, "provider_type", None) or "gemini"
        model_override = getattr(event, "model_override", None)
        logger.info(
            "agent_task_run_enqueued",
            task_id=str(task_id),
            provider_type=provider_type,
        )
        run_agent_task.delay(str(task_id), provider_type, model_override)


def _build_agent(provider_type: str, model_override: str | None):
    """Build the reasoning provider exactly like the create-task route does."""
    from apps.backend.agent.agent import AtlasAgent
    from apps.backend.agent.providers.mock import MockAgentProvider
    from apps.backend.agent.providers.router import (
        ProviderRouter,
        build_provider_instance,
    )
    from apps.backend.agent.tools.registry import ToolRegistry

    if provider_type == "mock":
        return AtlasAgent(provider=MockAgentProvider(), registry=ToolRegistry())
    primary = build_provider_instance(provider_type, model_override)
    return AtlasAgent(provider=ProviderRouter(primary=primary) if primary else ProviderRouter())


def _status_label(value) -> str:
    return str(getattr(value, "value", value))


def run_agent_task_core(
    db: Session,
    task_id: uuid_module.UUID,
    provider_type: str,
    model_override: str | None,
    instance_id: str | None = None,
) -> str | None:
    """Execute one agent run checkpointed in the DB.

    Returns the terminal (or parked) status label, or None when the row is
    missing / not owned by this run (idempotent no-op).
    """
    from apps.backend.routers.agent import (
        _agent_tasks_db,
        _persist_task,
    )

    record = db.get(AgentTaskRecord, task_id)
    if record is None:
        logger.info("agent_task_run_skipped_missing", task_id=str(task_id))
        return None

    snapshot = dict(record.snapshot or {})
    task = AgentTask.model_validate(snapshot)

    # A task already waiting on the user or on dispatched executions must not
    # be re-entered by a duplicate/redelivered message. Only the statuses the
    # loop itself may drive are claimable.
    claimable = {
        AgentTaskStatus.PENDING.value,
        AgentTaskStatus.PLANNING.value,
        AgentTaskStatus.EXECUTING.value,
        AgentTaskStatus.REPAIRING.value,
        AgentTaskStatus.RESUMED.value,
        AgentTaskStatus.EVALUATING.value,
        AgentTaskStatus.REPORTING.value,
    }
    if _status_label(task.status) not in claimable:
        logger.info("agent_task_run_skipped_not_claimable", task_id=str(task_id))
        return None

    # Register the live object so tools (execution_tools, evaluation_tools,
    # dataset_tools) can attach execution_ids / report lineage to it.
    _agent_tasks_db[task.task_id] = task
    try:
        agent = _build_agent(provider_type, model_override)
        task = agent.run_task(task, db)
        _persist_task(db, task, instance_id=instance_id)
        return _status_label(task.status)
    except Exception:
        logger.exception("agent_task_run_failed", task_id=str(task_id))
        task.status = AgentTaskStatus.FAILED
        task.completed_at = datetime.now(UTC)
        task.error_detail = "Infrastructure failure inside agent loop"
        task.add_trace("TASK_FAILED", {"error": "Infrastructure failure inside agent loop"})
        _persist_task(db, task, instance_id=instance_id)
        raise
    finally:
        _agent_tasks_db.pop(task.task_id, None)


from apps.backend.worker.celery_app import celery_app  # noqa: E402


@celery_app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=1500,
    time_limit=1560,
)
def run_agent_task(
    self,
    task_id_str: str,
    provider_type: str = "gemini",
    model_override: Optional[str] = None,
):
    """Enqueued form of ``run_agent_task_core`` (durable worker execution)."""
    from atlas_db.core.session import SessionLocal

    try:
        task_id = uuid_module.UUID(str(task_id_str))
    except ValueError:
        logger.error("agent_task_run_invalid_task_id", raw=task_id_str)
        return None

    instance_id = f"{self.request.hostname or 'worker'}:{self.request.id or ''}"
    try:
        with SessionLocal() as db:
            return run_agent_task_core(db, task_id, provider_type, model_override, instance_id)
    except Exception:
        if self.request.retries >= self.max_retries:
            logger.exception(
                "agent_task_run_max_retries_exceeded",
                task_id=task_id_str,
            )
            raise
        raise self.retry(exc=None, countdown=2**self.request.retries)
