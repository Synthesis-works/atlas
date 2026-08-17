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
from apps.backend.dependencies import get_db_session
from atlas_db.core.session import SessionLocal

router = APIRouter(prefix="/agent", tags=["Atlas Agent"])


def _persist_task(db: Session, task: "AgentTask") -> None:
    """Persist (or refresh) the AgentTask snapshot so it survives backend restarts."""
    from atlas_db.models.agent import AgentTaskRecord

    snapshot = task.model_dump(mode="json")
    record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task.task_id).first()
    if record is None:
        record = AgentTaskRecord(
            task_id=task.task_id,
            goal=task.goal,
            status=task.status.value,
            snapshot=snapshot,
        )
        db.add(record)
    else:
        record.goal = task.goal
        record.status = task.status.value
        record.snapshot = snapshot
    db.commit()

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
            _persist_task(db, task)
        db.close()


@router.post("/tasks", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_agent_task(
    payload: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    task = AgentTask(
        goal=payload.goal,
        granted_permissions=payload.permissions,
        primary_provider=payload.provider,
    )
    if payload.model is not None:
        task.model = payload.model
    _agent_tasks_db[task.task_id] = task
    _persist_task(db, task)

    if payload.provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(task, db)
        _persist_task(db, task)
    else:
        background_tasks.add_task(
            _run_agent_task_background, task.task_id, SessionLocal, payload.provider, payload.model
        )

    return _serialize_agent_task(task)


@router.get("/tasks/{task_id}", response_model=dict[str, Any])
def get_agent_task(task_id: UUID, db: Session = Depends(get_db_session)):
    task = _agent_tasks_db.get(task_id)
    if not task:
        from atlas_db.models.agent import AgentTaskRecord

        record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found."
            )
        task = AgentTask.model_validate(record.snapshot)

    return _serialize_agent_task(task)


@router.get("/reports/{report_id}", response_model=dict[str, Any])
def get_agent_report(report_id: str, db: Session = Depends(get_db_session)):
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

    metrics = [
        {"metric_name": m.metric_name, "metric_value": m.metric_value} for m in version.metrics
    ]

    # Resolve the real benchmark ID when possible:
    # ReportVersion.execution_id -> Execution.benchmark_version_id -> BenchmarkVersion.benchmark_id
    # If the linkage cannot be resolved, return null rather than inventing one.
    benchmark_id = None
    if version.execution_id:
        from atlas_db.models.execution import Execution as DBExecution
        from atlas_db.models.authoring import BenchmarkVersion as DBBenchmarkVersion

        execution = db.query(DBExecution).filter(DBExecution.id == version.execution_id).first()
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
def list_agent_tasks(db: Session = Depends(get_db_session)):
    from atlas_db.models.agent import AgentTaskRecord

    live = list(_agent_tasks_db.values())
    live_ids = {t.task_id for t in live}
    records = (
        db.query(AgentTaskRecord).order_by(AgentTaskRecord.created_at.desc()).all()
    )
    persisted = [
        AgentTask.model_validate(r.snapshot)
        for r in records
        if r.task_id not in live_ids
    ]
    tasks = list(reversed(live)) + persisted
    return [_serialize_agent_task(t) for t in tasks]


@router.delete("/tasks", response_model=dict[str, Any])
def clear_agent_tasks(db: Session = Depends(get_db_session)):
    from atlas_db.models.agent import AgentTaskRecord

    _agent_tasks_db.clear()
    db.query(AgentTaskRecord).delete()
    db.commit()
    return {"status": "success", "message": "All agent tasks cleared."}


@router.delete("/tasks/{task_id}", response_model=dict[str, Any])
def delete_agent_task(task_id: UUID, db: Session = Depends(get_db_session)):
    from atlas_db.models.agent import AgentTaskRecord

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
    task_id: UUID, payload: TaskApprovalRequest, db: Session = Depends(get_db_session)
):
    task = _agent_tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found."
        )

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

    agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
    agent.run_task(task, db)
    _persist_task(db, task)

    return {
        "task_id": str(task.task_id),
        "status": task.status.value,
        "message": "Task approved and resumed successfully.",
    }


@router.post("/tasks/{task_id}/cancel", response_model=dict[str, Any])
def cancel_agent_task(task_id: UUID):
    task = _agent_tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found."
        )

    task.status = AgentTaskStatus.CANCELLED
    task.add_trace("TASK_CANCELLED", {"reason": "User manual cancellation"})

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
):
    task = _agent_tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found."
        )

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

    if task.primary_provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(task, db)
        _persist_task(db, task)
    else:
        background_tasks.add_task(
            _run_agent_task_background,
            task.task_id,
            SessionLocal,
            task.primary_provider,
            task.model,
        )

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
):
    old_task = _agent_tasks_db.get(task_id)
    if not old_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found."
        )

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
        background_tasks.add_task(
            _run_agent_task_background,
            new_task.task_id,
            SessionLocal,
            new_task.primary_provider,
            new_task.model,
        )

    return {
        "task_id": str(new_task.task_id),
        "status": new_task.status.value,
        "message": f"Successfully launched run-again task '{new_task_id}' from source '{task_id}'.",
    }


@router.get("/tools", response_model=list[dict[str, Any]])
def list_agent_tools():
    return _tool_registry.list_tools()


@router.get("/providers", response_model=list[dict[str, Any]])
def list_agent_providers():
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
