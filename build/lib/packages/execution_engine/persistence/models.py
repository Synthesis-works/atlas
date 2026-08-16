import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from atlas_db.core.base import Base, BaseMixin
from packages.execution_engine.domain.models import ArtifactType, AttemptStatus, ExecutionState


class ExecutionModel(Base, BaseMixin):
    __tablename__ = "ee_executions"
    __table_args__ = {"extend_existing": True}

    benchmark_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[ExecutionState] = mapped_column(
        SQLEnum(ExecutionState, name="execution_status", create_type=False), nullable=False
    )
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    project_id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4)
    target_model: Mapped[str] = mapped_column(String(255), default="test-model")

    attempts: Mapped[list["ExecutionAttemptModel"]] = relationship(
        "ExecutionAttemptModel",
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="ExecutionAttemptModel.attempt_number",
    )


class ExecutionAttemptModel(Base):
    __tablename__ = "execution_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ee_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        SQLEnum(AttemptStatus, name="attempt_status"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    execution: Mapped["ExecutionModel"] = relationship(
        "ExecutionModel", back_populates="attempts", foreign_keys=[execution_id]
    )

    lease: Mapped[Optional["LeaseModel"]] = relationship(
        "LeaseModel", back_populates="attempt", uselist=False, cascade="all, delete-orphan"
    )

    artifacts: Mapped[list["ArtifactModel"]] = relationship(
        "ArtifactModel", back_populates="attempt", cascade="all, delete-orphan"
    )


class LeaseModel(Base):
    __tablename__ = "execution_leases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_attempts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    attempt: Mapped["ExecutionAttemptModel"] = relationship(
        "ExecutionAttemptModel", back_populates="lease"
    )


class ArtifactModel(Base):
    __tablename__ = "execution_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ArtifactType] = mapped_column(
        SQLEnum(ArtifactType, name="execution_artifact_type"), nullable=False
    )
    storage_uri: Mapped[str] = mapped_column(String, nullable=False)

    attempt: Mapped["ExecutionAttemptModel"] = relationship(
        "ExecutionAttemptModel", back_populates="artifacts"
    )
