from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
