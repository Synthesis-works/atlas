"""Hosted agent-session DTOs — mirror ``apps/backend/routers/agent_sessions.py``.

The sessions router returns bare dicts (no ``APIResponse`` envelope), like the
execution endpoints.  ``AgentSessionRead`` mirrors ``_serialize_session`` and
``AgentSessionTurnRead`` mirrors the ``{session, reply}`` shapes returned by the
message/approve/clarify/cancel endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AgentSessionCreate(BaseModel):
    """Request body for ``POST /api/v1/agent/sessions``."""

    goal: str
    title: str | None = None
    provider: str = "gemini"
    model: str | None = None
    project_id: str | None = None


class AgentSessionMessageRequest(BaseModel):
    """Request body for ``POST /api/v1/agent/sessions/{id}/messages``."""

    message: str


class AgentApprovalRequest(BaseModel):
    """Request body for ``POST /api/v1/agent/sessions/{id}/approve``."""

    approval_token: str


class AgentClarificationRequest(BaseModel):
    """Request body for ``POST /api/v1/agent/sessions/{id}/clarify``."""

    answer: str
    clarification_id: str | None = None


class AgentSessionMessage(BaseModel):
    """A single entry in the session transcript."""

    model_config = ConfigDict(protected_namespaces=())

    role: str
    content: str
    task_id: str | None = None
    created_at: str | None = None


class AgentPendingAction(BaseModel):
    """Shape of ``pending_action`` when the session is blocked on input."""

    model_config = ConfigDict(protected_namespaces=())

    action: str
    task_id: str
    tool_name: str | None = None
    approval_token_required: bool | None = None
    clarification_id: str | None = None
    question: str | None = None
    message: str | None = None


class AgentSessionRead(BaseModel):
    """A hosted conversational agent session."""

    model_config = ConfigDict(protected_namespaces=())

    session_id: str
    title: str | None = None
    status: str
    state: str
    provider: str
    project_id: str | None = None
    current_task_id: str | None = None
    pending_action: AgentPendingAction | None = None
    transcript: list[AgentSessionMessage]
    created_at: str | None = None
    updated_at: str | None = None
    last_activity_at: str | None = None


class AgentSessionTurnRead(BaseModel):
    """Response shape of the message/approve/clarify/cancel endpoints."""

    model_config = ConfigDict(protected_namespaces=())

    session: AgentSessionRead
    reply: str | None = None
