"""P1 Hosted Conversational Session API for the Atlas Agent.

A session is a persistent, bounded conversation between an authenticated user
and the agent. Each turn appends a user message and either (a) starts a fresh
``AgentTask`` whose goal is the message, (b) answers an outstanding
clarification for the active task, or (c) is rejected (409) while a task is
mid-flight awaiting approval/execution.

Security model (all server-side, derived from the caller's JWT):
- sessions are owned by ``created_by_user_id``; the owner is the only principal
  that can read/modify a session;
- every task a session spawns carries a project anchor (when the session has
  one) and the JWT ownership stamps. The agent task always runs with a
  *server-set* minimal grant (``READ`` only), so any WRITE/EXECUTE/PUBLISH tool
  parks in ``WAITING_FOR_APPROVAL`` and the user must explicitly approve it via
  ``POST /sessions/{id}/approve``. Hosted mutations are never auto-approved.
- the same Bearer JWT mechanism used by the rest of the API is reused; there is
  no second auth mechanism.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus
from apps.backend.dependencies import (
    TokenClaims,
    get_db_session,
    require_authenticated,
)
from apps.backend.rate_limit import (
    enforce_agent_minute_rate_limit,
    enforce_agent_task_create_limit,
)
from apps.backend.routers.agent import (
    _agent_tasks_db,
    _dispatch_agent_run,
    _persist_task,
    _tool_registry,
)
from atlas_db.models.agent import AgentSession

router = APIRouter(prefix="/agent/sessions", tags=["Atlas Agent Sessions"])

TERMINAL_STATUSES = {
    AgentTaskStatus.COMPLETED,
    AgentTaskStatus.FAILED,
    AgentTaskStatus.CANCELLED,
}

MAX_TRANSCRIPT_MESSAGES = 30

# Session lifecycle states (derived for clients; DB column holds ACTIVE/ARCHIVED)
STATE_READY = "READY"
STATE_RUNNING = "RUNNING"
STATE_AWAITING_APPROVAL = "AWAITING_APPROVAL"
STATE_AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
STATE_WAITING_FOR_EXECUTION = "WAITING_FOR_EXECUTION"


class SessionCreateRequest(BaseModel):
    goal: str = Field(description="The user's first message; becomes the initial task goal.")
    title: Optional[str] = Field(
        default=None,
        description="Optional session title. Defaults to the first message.",
    )
    provider: str = Field(
        default="gemini",
        description="Agent reasoning provider: 'gemini', 'groq', 'mistral', or 'mock' (test only).",
    )
    model: Optional[str] = Field(
        default=None, description="Model override. If omitted, the provider default is used."
    )
    project_id: Optional[UUID] = Field(
        default=None,
        description="Anchor project for this session. Mutations are authorized against it.",
    )


class SessionMessageRequest(BaseModel):
    message: str = Field(description="User message for the next agent turn.")


class SessionApprovalRequest(BaseModel):
    approval_token: str = Field(description="Token authorizing the pending tool action.")


class SessionClarificationRequest(BaseModel):
    answer: str = Field(description="The user's answer to the pending clarification.")
    clarification_id: Optional[str] = Field(
        default=None, description="Optional clarification id to verify against."
    )


# --- helpers ----------------------------------------------------------------


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _derive_state(task: AgentTask | None) -> str:
    if task is None:
        return STATE_READY
    if task.status == AgentTaskStatus.WAITING_FOR_APPROVAL:
        return STATE_AWAITING_APPROVAL
    if task.status == AgentTaskStatus.WAITING_FOR_CLARIFICATION:
        return STATE_AWAITING_CLARIFICATION
    if task.status == AgentTaskStatus.WAITING_FOR_EXECUTION:
        return STATE_WAITING_FOR_EXECUTION
    if task.status in TERMINAL_STATUSES:
        return STATE_READY
    return STATE_RUNNING


def _assistant_message_for_task(task: AgentTask) -> str | None:
    """Turn the task's current lifecycle position into a transcript message."""
    if task.status == AgentTaskStatus.COMPLETED:
        if isinstance(task.final_result, dict):
            summary = task.final_result.get("summary")
            if summary:
                return str(summary)
        return "Task completed successfully."
    if task.status == AgentTaskStatus.FAILED:
        return f"Task failed: {task.error_detail or 'unknown error'}"
    if task.status == AgentTaskStatus.CANCELLED:
        return "Task cancelled."
    if task.status == AgentTaskStatus.WAITING_FOR_CLARIFICATION:
        question = task.clarification_prompt or task.clarification_request
        return f"I need a clarification: {question or 'please clarify.'}"
    if task.status == AgentTaskStatus.WAITING_FOR_APPROVAL:
        tool_name = (task.pending_tool_call or {}).get("tool_name")
        return f"Tool '{tool_name or 'this tool'}' requires your approval before I can proceed."
    if task.status == AgentTaskStatus.WAITING_FOR_EXECUTION:
        return "Executions dispatched. I'll resume automatically when they complete."
    return None


def _pending_action(task: AgentTask | None) -> dict[str, Any] | None:
    if task is None:
        return None
    if task.status == AgentTaskStatus.WAITING_FOR_APPROVAL:
        args = task.pending_tool_call or {}
        return {
            "action": "approve",
            "task_id": str(task.task_id),
            "tool_name": args.get("tool_name"),
            "approval_token_required": True,
            "approval_token": task.approval_token,
        }
    if task.status == AgentTaskStatus.WAITING_FOR_CLARIFICATION:
        return {
            "action": "clarify",
            "task_id": str(task.task_id),
            "clarification_id": task.clarification_id,
            "question": task.clarification_prompt or task.clarification_request,
        }
    if task.status == AgentTaskStatus.WAITING_FOR_EXECUTION:
        return {
            "action": "wait",
            "task_id": str(task.task_id),
            "message": "Executions in flight; the session will resume automatically.",
        }
    return None


def _serialize_session(session: AgentSession, task: AgentTask | None) -> dict[str, Any]:
    return {
        "session_id": str(session.id),
        "title": session.title,
        "status": session.status,
        "state": _derive_state(task),
        "provider": session.provider,
        "project_id": str(session.project_id) if session.project_id else None,
        "current_task_id": str(session.current_task_id) if session.current_task_id else None,
        "pending_action": _pending_action(task),
        "transcript": session.transcript,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "last_activity_at": session.last_activity_at.isoformat()
        if session.last_activity_at
        else None,
    }


def _load_session_owner(db: Session, session_id: UUID, claims: TokenClaims) -> AgentSession:
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AgentSession '{session_id}' not found.",
        )
    if session.created_by_user_id != claims.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this agent session.",
        )
    return session


def _require_active_session(session: AgentSession) -> None:
    """Reject turn continuation once the session has been archived."""
    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is archived; it can no longer receive turns.",
        )


def _load_session_task(db: Session, session: AgentSession) -> AgentTask | None:
    """Resolve the session's current task from its persisted snapshot."""
    if session.current_task_id is None:
        return None
    task_id = session.current_task_id
    from atlas_db.models.agent import AgentTaskRecord

    record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
    if record is None:
        return _agent_tasks_db.get(task_id)
    task = AgentTask.model_validate(record.snapshot)
    _agent_tasks_db[task_id] = task
    return task


def _touch(session: AgentSession, db: Session) -> None:
    session.updated_at = datetime.now(UTC)
    session.last_activity_at = datetime.now(UTC)
    db.commit()


def _append_message(
    session: AgentSession, db: Session, *, role: str, content: str, task_id: UUID | None
) -> None:
    messages = list(session.transcript or [])
    messages.append(
        {
            "role": role,
            "content": content,
            "task_id": str(task_id) if task_id else None,
            "created_at": _utcnow(),
        }
    )
    if len(messages) > MAX_TRANSCRIPT_MESSAGES:
        messages = messages[-MAX_TRANSCRIPT_MESSAGES:]
    session.transcript = messages
    _touch(session, db)


def _has_assistant_message(session: AgentSession, task_id: UUID) -> bool:
    tail = session.transcript or []
    return any(m.get("role") == "assistant" and m.get("task_id") == str(task_id) for m in tail)


def _sync_transcript(session: AgentSession, db: Session) -> None:
    """Append a per-task assistant message exactly once, keeping the transcript
    in sync with the task's current position. Bounded client-side by trimming."""
    task = _load_session_task(db, session)
    if task is None:
        return
    message = _assistant_message_for_task(task)
    if message is None:
        return
    if _has_assistant_message(session, task.task_id):
        return
    _append_message(session, db, role="assistant", content=message, task_id=task.task_id)


def _create_session_task(
    db: Session,
    session: AgentSession,
    claims: TokenClaims,
    *,
    goal: str,
    provider: str,
    model: Optional[str],
) -> AgentTask:
    """Spawn a task for a session with server-set minimal permissions.

    Only READ is granted: any WRITE/EXECUTE/PUBLISH tool automatically parks in
    WAITING_FOR_APPROVAL and requires an explicit user approval. The task
    inherits the session's project anchor so the tool-scope gate can authorize
    mutations against a real, caller-owned project.
    """
    task = AgentTask(
        goal=goal,
        granted_permissions=[AgentPermission.READ],
        primary_provider=provider,
        created_by_user_id=claims.sub,
        organization_id=claims.organization_id,
        project_id=session.project_id,
    )
    if model is not None:
        task.model = model
    _agent_tasks_db[task.task_id] = task
    _persist_task(db, task)
    session.current_task_id = task.task_id
    session.title = session.title or goal[:80]
    _touch(session, db)
    return task


def _run_or_dispatch(background_tasks: BackgroundTasks, db: Session, task: AgentTask) -> None:
    """Run the task synchronously for the mock provider (fast tests), else
    dispatch via the same background path as ``/agent/tasks``."""
    from apps.backend.agent.agent import AtlasAgent
    from apps.backend.agent.providers.mock import MockAgentProvider

    if task.primary_provider == "mock":
        agent = AtlasAgent(provider=MockAgentProvider(), registry=_tool_registry)
        agent.run_task(task, db)
        _persist_task(db, task)
    else:
        _dispatch_agent_run(background_tasks, db, task.task_id, task.primary_provider, task.model)


# --- endpoints --------------------------------------------------------------


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_agent_session(
    payload: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_task_create_limit),
):
    session = AgentSession(
        id=uuid.uuid4(),
        created_by_user_id=claims.sub,
        organization_id=claims.organization_id,
        title=payload.title,
        provider=payload.provider,
        model=payload.model,
        project_id=payload.project_id,
        transcript=[],
    )
    if payload.project_id is not None:
        from apps.backend.authz import ProjectAuthorizationService
        from atlas_db.models.core import OrganizationRole

        ProjectAuthorizationService(db).authorize_project_access(
            project_id=payload.project_id,
            user_id=claims.sub,
            allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER],
        )
    db.add(session)
    db.commit()

    task = _create_session_task(
        db, session, claims, goal=payload.goal, provider=payload.provider, model=payload.model
    )
    _append_message(session, db, role="user", content=payload.goal, task_id=task.task_id)
    _run_or_dispatch(background_tasks, db, task)
    _sync_transcript(session, db)

    return _serialize_session(session, _load_session_task(db, session))


@router.get("", response_model=list[dict[str, Any]])
def list_agent_sessions(
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    sessions = (
        db.query(AgentSession)
        .filter(
            AgentSession.created_by_user_id == claims.sub,
            AgentSession.status == "ACTIVE",
        )
        .order_by(AgentSession.updated_at.desc())
        .all()
    )
    result = []
    for session in sessions:
        _sync_transcript(session, db)
        result.append(_serialize_session(session, _load_session_task(db, session)))
    return result


@router.get("/{session_id}", response_model=dict[str, Any])
def get_agent_session(
    session_id: UUID,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    session = _load_session_owner(db, session_id, claims)
    task = _load_session_task(db, session)
    _sync_transcript(session, db)
    return _serialize_session(session, _load_session_task(db, session))


@router.delete("/{session_id}", response_model=dict[str, Any])
def delete_agent_session(
    session_id: UUID,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    session = _load_session_owner(db, session_id, claims)
    session.status = "ARCHIVED"
    db.commit()
    return {"status": "success", "message": f"Session {session_id} archived."}


@router.post("/{session_id}/messages", response_model=dict[str, Any])
def send_agent_session_message(
    session_id: UUID,
    payload: SessionMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_task_create_limit),
):
    session = _load_session_owner(db, session_id, claims)
    _require_active_session(session)
    task = _load_session_task(db, session)
    state = _derive_state(task)

    if state == STATE_AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tool approval is pending for this session. Approve or cancel before sending a new message.",
        )
    if state in (STATE_RUNNING, STATE_WAITING_FOR_EXECUTION):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The session is busy in an active turn. Wait for it to complete.",
        )

    if state == STATE_AWAITING_CLARIFICATION:
        # The message is the clarification answer; reuses the task's clarify flow.
        from apps.backend.agent.agent import AtlasAgent

        assert task is not None
        task.clarification_answer = payload.message
        agent = AtlasAgent()
        fingerprint = agent._normalize_clarification(
            task.clarification_request or task.clarification_prompt or ""
        )
        task.past_clarifications.append(
            {
                "question": task.clarification_request
                or task.clarification_prompt
                or "Clarification",
                "answer": payload.message,
                "fingerprint": fingerprint,
                "answered_at": _utcnow(),
            }
        )
        task.clarification_request = None
        task.clarification_prompt = None
        task.clarification_id = None
        task.clarification_requested_at = None
        task.status = AgentTaskStatus.PLANNING
        _append_message(session, db, role="user", content=payload.message, task_id=task.task_id)
        _run_or_dispatch(background_tasks, db, task)
        _sync_transcript(session, db)
    else:
        if task is not None and task.status in TERMINAL_STATUSES:
            _sync_transcript(session, db)
        new_task = _create_session_task(
            db,
            session,
            claims,
            goal=payload.message,
            provider=session.provider or "gemini",
            model=session.model,
        )
        _append_message(session, db, role="user", content=payload.message, task_id=new_task.task_id)
        _run_or_dispatch(background_tasks, db, new_task)
        _sync_transcript(session, db)
        task = new_task

    task = _load_session_task(db, session)
    return {
        "session": _serialize_session(session, task),
        "reply": _assistant_message_for_task(task) if task else None,
    }


@router.post("/{session_id}/approve", response_model=dict[str, Any])
def approve_agent_session(
    session_id: UUID,
    payload: SessionApprovalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    session = _load_session_owner(db, session_id, claims)
    _require_active_session(session)
    task = _load_session_task(db, session)

    if task is None or task.status != AgentTaskStatus.WAITING_FOR_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no pending tool approval.",
        )
    if task.approval_token != payload.approval_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid approval token."
        )

    pending = task.pending_tool_call
    if pending:
        tool = _tool_registry.get_tool(pending.get("tool_name", ""))
        if tool and tool.required_permission not in task.granted_permissions:
            task.granted_permissions.append(tool.required_permission)

    task.pending_tool_call = None
    task.approval_token = None
    task.status = AgentTaskStatus.EXECUTING
    _persist_task(db, task)

    _run_or_dispatch(background_tasks, db, task)
    _sync_transcript(session, db)
    task = _load_session_task(db, session)
    return {
        "session": _serialize_session(session, task),
        "reply": _assistant_message_for_task(task) if task else None,
    }


@router.post("/{session_id}/clarify", response_model=dict[str, Any])
def clarify_agent_session(
    session_id: UUID,
    payload: SessionClarificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    session = _load_session_owner(db, session_id, claims)
    _require_active_session(session)
    task = _load_session_task(db, session)

    if task is None or task.status != AgentTaskStatus.WAITING_FOR_CLARIFICATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no pending clarification.",
        )
    if (
        task.clarification_id
        and payload.clarification_id
        and task.clarification_id != payload.clarification_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clarification ID mismatch. Expected '{task.clarification_id}', got '{payload.clarification_id}'.",
        )

    from apps.backend.agent.agent import AtlasAgent

    agent = AtlasAgent()
    fingerprint = agent._normalize_clarification(
        task.clarification_request or task.clarification_prompt or ""
    )
    task.past_clarifications.append(
        {
            "question": task.clarification_request or task.clarification_prompt or "Clarification",
            "answer": payload.answer,
            "fingerprint": fingerprint,
            "answered_at": _utcnow(),
        }
    )
    task.clarification_request = None
    task.clarification_prompt = None
    task.clarification_id = None
    task.clarification_requested_at = None
    task.status = AgentTaskStatus.PLANNING

    _append_message(session, db, role="user", content=payload.answer, task_id=task.task_id)
    _run_or_dispatch(background_tasks, db, task)
    _sync_transcript(session, db)
    task = _load_session_task(db, session)
    return {
        "session": _serialize_session(session, task),
        "reply": _assistant_message_for_task(task) if task else None,
    }


@router.post("/{session_id}/cancel", response_model=dict[str, Any])
def cancel_agent_session(
    session_id: UUID,
    db: Session = Depends(get_db_session),
    claims: TokenClaims = Depends(require_authenticated),
    _: TokenClaims = Depends(enforce_agent_minute_rate_limit),
):
    session = _load_session_owner(db, session_id, claims)
    task = _load_session_task(db, session)

    if task is None or task.status in TERMINAL_STATUSES:
        return {
            "session": _serialize_session(session, task),
            "reply": None,
        }

    task.status = AgentTaskStatus.CANCELLED
    task.add_trace("TASK_CANCELLED", {"reason": "User manual cancellation"})
    _persist_task(db, task)
    _sync_transcript(session, db)
    task = _load_session_task(db, session)
    return {
        "session": _serialize_session(session, task),
        "reply": _assistant_message_for_task(task) if task else None,
    }
