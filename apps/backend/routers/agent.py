import os
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.mock import MockAgentProvider
from apps.backend.agent.providers.router import (
    ProviderRouter,
    build_provider_instance,
    get_configured_providers,
)
from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus
from apps.backend.agent.tools.registry import ToolRegistry
from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import (
    TokenClaims,
    get_db_session,
    require_authenticated,
)
from apps.backend.rate_limit import (
    enforce_agent_minute_rate_limit,
    enforce_agent_task_create_limit,
)
from atlas_db.core.session import SessionLocal
from atlas_db.models.core import OrganizationRole

router = APIRouter(prefix="/agent", tags=["Atlas Agent"])

# Read-level access to an agent-owned report requires any membership role.
READ_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
    OrganizationRole.VIEWER,
]


def _persist_task(db: Session, task: "AgentTask", instance_id: Optional[str] = None) -> None:
    """Persist (or refresh) the AgentTask snapshot so it survives backend restarts.

    ``instance_id`` records which process currently owns the live loop, together
    with a ``heartbeat_at`` liveness stamp. Both are written only while the task
    is actively executing; parked and terminal tasks carry no owner.
    """
    from atlas_db.models.agent import AgentTaskRecord

    snapshot = task.model_dump(mode="json")
    record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task.task_id).first()
    if record is None:
        record = AgentTaskRecord(
            task_id=task.task_id,
            goal=task.goal,
            status=task.status.value,
            snapshot=snapshot,
            created_by_user_id=task.created_by_user_id,
            organization_id=task.organization_id,
        )
        db.add(record)
    else:
        record.goal = task.goal
        record.status = task.status.value
        record.snapshot = snapshot
        record.created_by_user_id = task.created_by_user_id
        record.organization_id = task.organization_id
    if instance_id is not None:
        record.instance_id = instance_id
        record.heartbeat_at = datetime.now(UTC)
    db.commit()


def _instance_handle() -> str:
    """Stable-ish short id for the current process ownership claims."""
    import socket

    return f"{socket.gethostname()}:{os.getpid()}"


def _load_agent_task(db: Session, task_id: UUID) -> Optional["AgentTask"]:
    """Resolve a task from its persisted snapshot, the source of truth.

    The worker parks/runs the task in its own process and checkpoints every
    state transition to the DB; the creating API instance's in-memory
    ``_agent_tasks_db`` copy would otherwise stay stale (e.g. PENDING forever)
    for the lifetime of that warm lambda. Reads and mutations therefore
    converge on the persisted row: rehydrate it, refresh this process's
    working copy, and return it. The live object is only a fallback when no
    row exists yet.
    """
    from atlas_db.models.agent import AgentTaskRecord

    record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
    if record is None:
        return _agent_tasks_db.get(task_id)
    task = AgentTask.model_validate(record.snapshot)
    _agent_tasks_db[task_id] = task
    return task


def _require_task_owner(db: Session, task_id: UUID, claims: TokenClaims) -> AgentTask:
    """Resolve a persisted task and enforce owner-only access.

    Tasks created before P0 auth hardening carry a NULL ``created_by_user_id``
    and must never surface to any user (403), even to users who know the id.
    """
    from atlas_db.models.agent import AgentTaskRecord

    user_id = claims.sub
    record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
    if record is None:
        task = _agent_tasks_db.get(task_id)
        if task is not None and task.created_by_user_id == user_id:
            return task
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found."
        )
    task = AgentTask.model_validate(record.snapshot)
    if task.created_by_user_id is None or task.created_by_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this agent task.",
        )
    _agent_tasks_db[task_id] = task
    return task


# In-memory storage for active agent tasks (backed by DB models)
_agent_tasks_db: dict[UUID, AgentTask] = {}
_tool_registry = ToolRegistry()


class TaskCreateRequest(BaseModel):
    goal: str = Field(description="Goal for the Atlas Agent to accomplish.")
    provider: str = Field(
        default="gemini",
        description="Agent reasoning provider: 'gemini', 'groq', 'mistral', or 'mock' (test only).",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model override. If omitted, the provider's configured default is used.",
    )
    permissions: list[AgentPermission] = Field(
        default_factory=lambda: [
            AgentPermission.READ,
            AgentPermission.WRITE,
            AgentPermission.EXECUTE,
            AgentPermission.PUBLISH,
        ],
        description="Permissions granted to the agent for this task.",
    )


class TaskApprovalRequest(BaseModel):
    approval_token: str = Field(description="Token authorizing the pending tool action.")


def _serialize_agent_task(task: AgentTask) -> dict[str, Any]:
    """Full, lossless serialization of an AgentTask used by create/detail/list endpoints."""
    return {
        "task_id": str(task.task_id),
        "goal": task.goal,
        "status": task.status.value,
        "step_count": task.step_count,
        "total_tool_calls": task.total_tool_calls,
        "repair_attempts": task.repair_attempts,
        "benchmark_id": task.benchmark_id,
        "benchmark_version_id": task.benchmark_version_id,
        "dataset_id": task.dataset_id,
        "dataset_version_id": task.dataset_version_id,
        "execution_ids": task.execution_ids,
        "report_id": task.report_id,
        "run_mode": task.run_mode,
        "source_task_id": str(task.source_task_id) if task.source_task_id else None,
        "plan": [p.model_dump() for p in task.plan],
        "tool_calls": [c.model_dump() for c in task.tool_calls],
        "observations": [o.model_dump() for o in task.observations],
        "execution_trace": [t.model_dump() for t in task.execution_trace],
        "pending_tool_call": task.pending_tool_call,
        "approval_token": task.approval_token,
        "clarification_prompt": task.clarification_prompt,
        "clarification_request": task.clarification_request,
        "clarification_id": task.clarification_id,
        "clarification_attempts": task.clarification_attempts,
        "clarification_answer": task.clarification_answer,
        "clarification_requested_at": task.clarification_requested_at.isoformat()
        if task.clarification_requested_at
        else None,
        "past_clarifications": task.past_clarifications,
        "final_result": task.final_result,
        "error_detail": task.error_detail,
        "primary_provider": task.primary_provider,
        "current_provider": task.current_provider,
        "created_at": task.started_at.isoformat() if task.started_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def _enqueue_agent_run(
    db: Session, task_id: UUID, provider_type: str, model_override: Optional[str]
) -> None:
    """Write an AgentRunRequestedEvent transactional-outbox row.

    The serverless API has no Celery broker, so the run is never enqueued
    directly. The Render worker's outbox sweep deserializes this row,
    ``AgentRunSubscriber`` enqueues ``run_agent_task`` on the worker's own
    broker, and the loop executes there with checkpoints to the DB.
    """
    from uuid import uuid4

    from atlas_db.models.outbox import OutboxMessage
    from apps.backend.core.telemetry import get_correlation_id, get_trace_id
    from apps.backend.worker.wake_client import notify_worker_wake
    from packages.execution_engine.domain.events import AgentRunRequestedEvent

    event = AgentRunRequestedEvent(
        timestamp=datetime.now(UTC),
        task_id=task_id,
        provider_type=provider_type,
        model_override=model_override,
    )
    db.add(
        OutboxMessage(
            event_id=uuid4(),
            aggregate_id=task_id,
            aggregate_type="AgentTask",
            event_type=event.event_type,
            event_version=event.event_version,
            schema_version=1,
            payload=event.to_dict(),
            trace_context={
                "correlation_id": get_correlation_id(),
                "trace_id": get_trace_id(),
            },
            occurred_at=event.timestamp,
        )
    )
    db.commit()
    notify_worker_wake()


def _dispatch_agent_run(
    background_tasks: BackgroundTasks,
    db: Session,
    task_id: UUID,
    provider_type: str,
    model_override: Optional[str],
) -> None:
    """Run one agent loop, either via the outbox->worker or in-process.

    ``AGENT_TASKS_CELERY_EXECUTION=true`` writes an ``AgentRunRequestedEvent``
    outbox row (worker-side enqueue; no broker needed on the API). Otherwise
    (local dev / unit tests) the loop runs via FastAPI BackgroundTasks on the
    same instance that created the task.
    """
    from apps.backend.config import settings

    if settings.agent_tasks_celery_execution:
        _enqueue_agent_run(db, task_id, provider_type, model_override)
        return
    background_tasks.add_task(
        _run_agent_task_background, task_id, SessionLocal, provider_type, model_override
    )


def _run_agent_task_background(
    task_id: UUID, db_session_factory, provider_type: str, model_override: Optional[str]
):
    db: Session = db_session_factory()
    task = _agent_tasks_db.get(task_id)
    try:
        if not task:
            return

        if provider_type == "mock":
            provider: BaseLLMProvider = MockAgentProvider()
        else:
            # Build the specific primary provider requested; let ProviderRouter handle fallbacks
            primary = build_provider_instance(provider_type, model_override)
            provider = ProviderRouter(primary=primary) if primary else ProviderRouter()

        agent = AtlasAgent(provider=provider, registry=_tool_registry)
        agent.run_task(task, db)
    finally:
        if task is not None:
            _persist_task(db, task, instance_id=_instance_handle())
        db.close()


@router.post("/tasks", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_agent_task(
    payload: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_task_create_limit),
):
    task = AgentTask(
        goal=payload.goal,
        granted_permissions=payload.permissions,
        primary_provider=payload.provider,
        created_by_user_id=claims.sub,
        organization_id=claims.organization_id,
    )
    task.model = payload.model
    _agent_tasks_db[task.task_id] = task
    _persist_task(db, task)

    if payload.provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(task, db)
        _persist_task(db, task)
    else:
        _dispatch_agent_run(background_tasks, db, task.task_id, payload.provider, payload.model)

    return _serialize_agent_task(task)


@router.get("/tasks/{task_id}", response_model=dict[str, Any])
def get_agent_task(
    task_id: UUID,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
):
    task = _require_task_owner(db, task_id, claims)

    return _serialize_agent_task(task)


@router.get("/reports/{report_id}", response_model=dict[str, Any])
def get_agent_report(
    report_id: str,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    project_authz: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    from atlas_db.models.reporting import ReportMetric, ReportVersion
    import uuid

    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found."
        )

    version = db.query(ReportVersion).filter(ReportVersion.id == report_uuid).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Report '{report_id}' not found."
        )

    # Agent-report ownership boundary: a report is readable through the agent
    # endpoint only when its lineage back to an execution (and thus a project)
    # can be resolved, and the caller is an active member of that project's
    # organization (any role). Legacy reports without execution linkage are
    # unreachable, matching how the endpoint treats unresolvable ownership.
    execution = None
    if version.execution_id:
        from atlas_db.models.execution import Execution as DBExecution

        execution = db.query(DBExecution).filter(DBExecution.id == version.execution_id).first()
    if not execution or not execution.project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this report.",
        )
    project_authz.authorize_project_access(
        project_id=execution.project_id,
        user_id=claims.sub,
        allowed_roles=READ_ROLES,
    )

    metrics = [
        {"metric_name": m.metric_name, "metric_value": m.metric_value} for m in version.metrics
    ]

    # Resolve the real benchmark ID when possible:
    # ReportVersion.execution_id -> Execution.benchmark_version_id -> BenchmarkVersion.benchmark_id
    # If the linkage cannot be resolved, return null rather than inventing one.
    benchmark_id = None
    if version.execution_id:
        from atlas_db.models.authoring import BenchmarkVersion as DBBenchmarkVersion

        if execution and execution.benchmark_version_id:
            benchmark_version = (
                db.query(DBBenchmarkVersion)
                .filter(DBBenchmarkVersion.id == execution.benchmark_version_id)
                .first()
            )
            if benchmark_version:
                benchmark_id = str(benchmark_version.benchmark_id)

    return {
        "report_id": str(version.id),
        "benchmark_id": benchmark_id,
        "title": version.report.name if version.report else "Benchmark Report",
        "summary": version.summary,
        "version_string": version.version_string,
        "execution_id": str(version.execution_id) if version.execution_id else None,
        "published": True,
        "created_at": version.created_at.isoformat(),
        "metrics": metrics,
    }


@router.get("/tasks", response_model=list[dict[str, Any]])
def list_agent_tasks(
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    """Read the caller's tasks from their persisted snapshots, the source of
    truth.

    The worker checkpoints all state transitions to ``agent_task_records`` in
    its own process; listing from the DB (instead of the process-local
    registry first) keeps statuses correct across instances rather than
    surfacing the stale working copy of whichever warm lambda created a task.
    Rows are filtered to the authenticated caller and legacy (owner-less)
    rows are never surfaced.
    """
    from atlas_db.models.agent import AgentTaskRecord

    records = (
        db.query(AgentTaskRecord)
        .filter(AgentTaskRecord.created_by_user_id == claims.sub)
        .order_by(AgentTaskRecord.created_at.desc())
        .all()
    )
    return [_serialize_agent_task(AgentTask.model_validate(r.snapshot)) for r in records]


@router.delete("/tasks", response_model=dict[str, Any])
def clear_agent_tasks(
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
):
    """Clear the caller's agent tasks (never other users' tasks)."""
    from atlas_db.models.agent import AgentTaskRecord

    user_id = claims.sub
    for tid, task in list(_agent_tasks_db.items()):
        if task.created_by_user_id == user_id:
            del _agent_tasks_db[tid]
    db.query(AgentTaskRecord).filter(AgentTaskRecord.created_by_user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": "All agent tasks cleared."}


@router.delete("/tasks/{task_id}", response_model=dict[str, Any])
def delete_agent_task(
    task_id: UUID,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
):
    from atlas_db.models.agent import AgentTaskRecord

    _require_task_owner(db, task_id, claims)
    if task_id in _agent_tasks_db:
        del _agent_tasks_db[task_id]
    record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
    if record:
        db.delete(record)
        db.commit()
        return {"status": "success", "message": f"Task {task_id} deleted."}
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/approve", response_model=dict[str, Any])
def approve_agent_task(
    task_id: UUID,
    payload: TaskApprovalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    task = _require_task_owner(db, task_id, claims)

    if task.status != AgentTaskStatus.WAITING_FOR_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is in status '{task.status}', not WAITING_FOR_APPROVAL.",
        )

    if task.approval_token != payload.approval_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid approval token."
        )

    # Grant required permission and resume execution
    pending = task.pending_tool_call
    if pending:
        tool = _tool_registry.get_tool(pending["tool_name"])
        if tool and tool.required_permission not in task.granted_permissions:
            task.granted_permissions.append(tool.required_permission)

    task.pending_tool_call = None
    task.approval_token = None
    task.status = AgentTaskStatus.EXECUTING
    _persist_task(db, task)

    if task.primary_provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(task, db)
        _persist_task(db, task)
    else:
        _dispatch_agent_run(background_tasks, db, task.task_id, task.primary_provider, task.model)

    return {
        "task_id": str(task.task_id),
        "status": task.status.value,
        "message": "Task approved and resumed successfully.",
    }


@router.post("/tasks/{task_id}/cancel", response_model=dict[str, Any])
def cancel_agent_task(
    task_id: UUID,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    task = _require_task_owner(db, task_id, claims)

    task.status = AgentTaskStatus.CANCELLED
    task.add_trace("TASK_CANCELLED", {"reason": "User manual cancellation"})
    _persist_task(db, task)

    return {
        "task_id": str(task.task_id),
        "status": task.status.value,
        "message": "Task cancelled successfully.",
    }


class TaskClarificationRequest(BaseModel):
    clarification_id: Optional[str] = Field(
        default=None, description="The ID of the clarification prompt."
    )
    answer: Optional[str] = Field(
        default=None, description="The user's response answering the clarification prompt."
    )
    response: Optional[str] = Field(
        default=None, description="Backwards compatible response field."
    )


@router.post("/tasks/{task_id}/clarify", response_model=dict[str, Any])
def clarify_agent_task(
    task_id: UUID,
    payload: TaskClarificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    task = _require_task_owner(db, task_id, claims)

    if task.status != AgentTaskStatus.WAITING_FOR_CLARIFICATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is in status '{task.status}', not WAITING_FOR_CLARIFICATION.",
        )

    answer_text = payload.answer or payload.response
    if not answer_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clarification answer/response is required.",
        )

    # Verify clarification_id if specified (and if task.clarification_id is present)
    if (
        task.clarification_id
        and payload.clarification_id
        and task.clarification_id != payload.clarification_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clarification ID mismatch. Expected '{task.clarification_id}', got '{payload.clarification_id}'.",
        )

    # Persist the answer
    task.clarification_answer = answer_text

    # Store in history/past_clarifications with fingerprint
    from apps.backend.agent.agent import AtlasAgent
    from datetime import datetime, UTC

    agent = AtlasAgent()
    fingerprint = agent._normalize_clarification(
        task.clarification_request or task.clarification_prompt or ""
    )

    task.past_clarifications.append(
        {
            "question": task.clarification_request
            or task.clarification_prompt
            or "Clarification request",
            "answer": answer_text,
            "fingerprint": fingerprint,
            "answered_at": datetime.now(UTC).isoformat(),
        }
    )

    # Clear active clarification prompt/id
    task.clarification_request = None
    task.clarification_prompt = None
    task.clarification_id = None
    task.clarification_requested_at = None

    task.add_trace("CLARIFICATION_RESPONDED", {"response": answer_text})

    # Transition task back to PLANNING status
    task.status = AgentTaskStatus.PLANNING

    _persist_task(db, task)

    if task.primary_provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(task, db)
        _persist_task(db, task)
    else:
        _dispatch_agent_run(background_tasks, db, task.task_id, task.primary_provider, task.model)

    return {
        "task_id": str(task.task_id),
        "status": task.status.value,
        "message": "Clarification submitted successfully, resuming execution.",
    }


@router.post("/tasks/{task_id}/run-again", response_model=dict[str, Any])
def run_agent_task_again(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    old_task = _require_task_owner(db, task_id, claims)

    # Create new task cloning parameters
    from uuid import uuid4

    new_task_id = uuid4()

    new_task = AgentTask(
        task_id=new_task_id,
        goal=old_task.goal,
        status=AgentTaskStatus.PENDING,
        granted_permissions=old_task.granted_permissions,
        run_mode="RERUN",
        source_task_id=old_task.task_id,
        benchmark_id=old_task.benchmark_id,
        benchmark_version_id=old_task.benchmark_version_id,
        dataset_id=old_task.dataset_id,
        dataset_version_id=old_task.dataset_version_id,
        primary_provider=old_task.primary_provider,
        model=old_task.model,
        created_by_user_id=old_task.created_by_user_id,
        organization_id=old_task.organization_id,
    )

    # Register in in-memory tasks database
    _agent_tasks_db[new_task_id] = new_task
    _persist_task(db, new_task)

    # Trace rerun start
    new_task.add_trace(
        "TASK_CLONED",
        {
            "source_task_id": str(old_task.task_id),
            "benchmark_version_id": old_task.benchmark_version_id,
            "dataset_version_id": old_task.dataset_version_id,
        },
    )

    # Start the task in background
    if new_task.primary_provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(new_task, db)
        _persist_task(db, new_task)
    else:
        _dispatch_agent_run(
            background_tasks, db, new_task.task_id, new_task.primary_provider, new_task.model
        )

    return {
        "task_id": str(new_task.task_id),
        "status": new_task.status.value,
        "message": f"Successfully launched run-again task '{new_task_id}' from source '{task_id}'.",
    }


@router.get("/tools", response_model=list[dict[str, Any]])
def list_agent_tools(claims: TokenClaims = Depends(require_authenticated)):
    return _tool_registry.list_tools()


@router.get("/providers", response_model=list[dict[str, Any]])
def list_agent_providers(claims: TokenClaims = Depends(require_authenticated)):
    """
    Returns the list of configured Agent reasoning providers.

    Configuration-aware: only providers with valid API keys present are included.
    Test-only providers (Atlas Mock) are never exposed here.
    The list is built from PROVIDER_REGISTRY in router.py — no live API calls.
    """
    configured = get_configured_providers(include_test_only=False)
    return [
        {
            "value": p.value,
            "label": p.label,
            "description": p.description,
            "model": p.model,
            "is_test_only": p.is_test_only,
            "configured": True,
            "enabled": not p.is_test_only,
            "status": "ready" if p.is_configured() else "unconfigured",
        }
        for p in configured
    ]
