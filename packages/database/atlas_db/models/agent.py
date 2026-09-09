from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from atlas_db.core.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AgentTaskRecord(Base):
    """
    Persisted snapshot of an Atlas Agent task.

    AgentTask objects are held in an in-memory registry while active, which is
    wiped on every backend restart. Persisting a full JSON snapshot of the task
    (task_id, goal, status, report_id, execution_ids, etc.) lets the Agent UI
    keep listing tasks and resolving the task -> execution -> report lineage
    after a restart.
    """

    __tablename__ = "agent_task_records"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    goal: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Execution ownership/liveness: which backend instance currently owns the
    # live loop (serverless instance id or durable worker id), and when it last
    # checkpointed. NULL when the task is parked/terminal and owned by no one.
    instance_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Identity/ownership of the authenticated user that created this task and
    # the organization the token claimed at creation time. NULL for legacy
    # (pre-P0) rows; those rows are never surfaced to any user.
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class ApiUsageCounter(Base):
    """
    DB-backed sliding-window usage counter for opt-in per-user rate limits.

    Rows are keyed by a scope string (e.g. ``agent:user:<uuid>``); ``count``
    accumulates within ``window_until``. Purged naturally by overwrite on window
    expiry. Serverless-safe: no in-memory or Redis dependency.
    """

    __tablename__ = "api_usage_counters"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentSession(Base):
    """A hosted conversational session between a user and the agent.

    Each session owns a bounded transcript (list of messages) and may hold a
    pointer to the currently-active (or most recent) ``AgentTaskRecord``. The
    transcript is lazily refreshed from the live task's observation list each
    time the session is read or the task completes.

    ``created_by_user_id`` is stamped from the JWT at creation time and is
    **never** NULL for rows created through the API. Ownership is enforced
    server-side; a user may only read/modify their own sessions.
    """

    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini")
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    # Bounded list of ConversationMessage dicts serialized as JSONB.
    # Max 30 entries enforced at the API layer before write.
    transcript: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
