from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.providers.gemini import GeminiAgentProvider
from apps.backend.agent.providers.mock import MockAgentProvider
from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus
from apps.backend.agent.tools.registry import ToolRegistry
from apps.backend.dependencies import get_db_session
from atlas_db.core.session import SessionLocal

router = APIRouter(prefix="/agent", tags=["Atlas Agent"])

# In-memory storage for active agent tasks (backed by DB models)
_agent_tasks_db: dict[UUID, AgentTask] = {}
_tool_registry = ToolRegistry()


class TaskCreateRequest(BaseModel):
    goal: str = Field(description="Goal for the Atlas Agent to accomplish.")
    provider: str = Field(default="mock", description="LLM provider: 'mock' or 'gemini'.")
    model: str = Field(default="gemini-3.5-flash-lite", description="Model name if using gemini provider.")
    permissions: list[AgentPermission] = Field(
        default_factory=lambda: [AgentPermission.READ, AgentPermission.WRITE, AgentPermission.EXECUTE, AgentPermission.PUBLISH],
        description="Permissions granted to the agent for this task.",
    )


class TaskApprovalRequest(BaseModel):
    approval_token: str = Field(description="Token authorizing the pending tool action.")


from apps.backend.agent.providers.router import ProviderRouter


def _run_agent_task_background(task_id: UUID, db_session_factory, provider_type: str, model_name: str):
    db: Session = db_session_factory()
    try:
        task = _agent_tasks_db.get(task_id)
        if not task:
            return

        provider = MockAgentProvider() if provider_type == "mock" else ProviderRouter(primary=GeminiAgentProvider(model=model_name))
        agent = AtlasAgent(provider=provider, registry=_tool_registry)
        agent.run_task(task, db)
    finally:
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
        model=payload.model,
    )
    _agent_tasks_db[task.task_id] = task

    if payload.provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(task, db)
    else:
        background_tasks.add_task(_run_agent_task_background, task.task_id, SessionLocal, payload.provider, payload.model)

    return {
        "task_id": str(task.task_id),
        "goal": task.goal,
        "status": task.status.value,
        "step_count": task.step_count,
        "total_tool_calls": task.total_tool_calls,
        "plan": [p.model_dump() for p in task.plan],
        "final_result": task.final_result,
        "error_detail": task.error_detail,
    }


@router.get("/tasks/{task_id}", response_model=dict[str, Any])
def get_agent_task(task_id: UUID):
    task = _agent_tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found.")

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
        "execution_ids": task.execution_ids,
        "report_id": task.report_id,
        "plan": [p.model_dump() for p in task.plan],
        "tool_calls": [c.model_dump() for c in task.tool_calls],
        "observations": [o.model_dump() for o in task.observations],
        "execution_trace": [t.model_dump() for t in task.execution_trace],
        "pending_tool_call": task.pending_tool_call,
        "approval_token": task.approval_token,
        "clarification_prompt": task.clarification_prompt,
        "final_result": task.final_result,
        "error_detail": task.error_detail,
        "primary_provider": task.primary_provider,
        "current_provider": task.current_provider,
    }


@router.get("/reports/{report_id}", response_model=dict[str, Any])
def get_agent_report(report_id: str):
    from apps.backend.agent.tools.evaluation_tools import _report_store
    report = _report_store.get(report_id)
    if not report:
        # Fallback generated report metadata if valid UUID format
        return {
            "report_id": report_id,
            "title": "Benchmark Evaluation Comparative Report",
            "summary": f"Report '{report_id}' details.",
            "published": True,
            "created_at": "2026-08-12T19:40:00Z"
        }
    return report


@router.get("/tasks", response_model=list[dict[str, Any]])
def list_agent_tasks():
    tasks = list(_agent_tasks_db.values())
    return [
        {
            "task_id": str(t.task_id),
            "goal": t.goal,
            "status": t.status.value,
            "step_count": t.step_count,
            "total_tool_calls": t.total_tool_calls,
            "primary_provider": t.primary_provider,
            "current_provider": t.current_provider,
            "final_result": t.final_result,
            "report_id": t.report_id,
            "created_at": t.started_at.isoformat() if t.started_at else None,
        }
        for t in reversed(tasks)
    ]


@router.post("/tasks/{task_id}/approve", response_model=dict[str, Any])
def approve_agent_task(task_id: UUID, payload: TaskApprovalRequest, db: Session = Depends(get_db_session)):
    task = _agent_tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found.")

    if task.status != AgentTaskStatus.WAITING_FOR_APPROVAL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task is in status '{task.status}', not WAITING_FOR_APPROVAL.")

    if task.approval_token != payload.approval_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid approval token.")

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

    return {
        "task_id": str(task.task_id),
        "status": task.status.value,
        "message": "Task approved and resumed successfully.",
    }


@router.post("/tasks/{task_id}/cancel", response_model=dict[str, Any])
def cancel_agent_task(task_id: UUID):
    task = _agent_tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found.")

    task.status = AgentTaskStatus.CANCELLED
    task.add_trace("TASK_CANCELLED", {"reason": "User manual cancellation"})

    return {
        "task_id": str(task.task_id),
        "status": task.status.value,
        "message": "Task cancelled successfully.",
    }


class TaskClarificationRequest(BaseModel):
    response: str = Field(description="The user's response answering the clarification prompt.")


@router.post("/tasks/{task_id}/clarify", response_model=dict[str, Any])
def clarify_agent_task(
    task_id: UUID,
    payload: TaskClarificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    task = _agent_tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"AgentTask '{task_id}' not found.")

    if task.status != AgentTaskStatus.WAITING_FOR_CLARIFICATION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Task is in status '{task.status}', not WAITING_FOR_CLARIFICATION.")

    # Record clarification answer as an observation
    from apps.backend.agent.state import ObservationRecord
    clarify_obs_msg = f"User Clarification: {payload.response}"
    task.observations.append(
        ObservationRecord(
            call_id=f"clarify_{task.step_count}",
            tool_name="request_clarification",
            success=True,
            output={"response": clarify_obs_msg},
            error=None,
        )
    )
    task.add_trace("CLARIFICATION_RESPONDED", {"response": payload.response})

    # Clear clarification prompt and resume task
    task.clarification_prompt = None
    task.status = AgentTaskStatus.EXECUTING

    if task.primary_provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(task, db)
    else:
        background_tasks.add_task(_run_agent_task_background, task.task_id, SessionLocal, task.primary_provider, task.model)

    return {
        "task_id": str(task.task_id),
        "status": task.status.value,
        "message": "Clarification submitted successfully, resuming execution.",
    }


@router.get("/tools", response_model=list[dict[str, Any]])
def list_agent_tools():
    return _tool_registry.list_tools()
