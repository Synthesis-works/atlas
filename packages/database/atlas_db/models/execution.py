import enum
import uuid
from datetime import datetime

from atlas_db.core.base import Base, BaseMixin, utcnow
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AdapterType(str, enum.Enum):
    LOCAL = "local"
    KUBERNETES = "kubernetes"
    AWS_BATCH = "aws_batch"


class ExecutionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    SCHEDULED = "SCHEDULED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class ArtifactType(str, enum.Enum):
    LOG = "log"
    LOGS = "LOGS"
    WEIGHTS = "weights"
    FILE = "file"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    EVALUATION_RESULT = "EVALUATION_RESULT"


class ExecutionAdapter(Base, BaseMixin):
    __tablename__ = "execution_adapters"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    type: Mapped[AdapterType] = mapped_column(
        ENUM(AdapterType, name="adapter_type"), nullable=False
    )

    versions: Mapped[list["ExecutionAdapterVersion"]] = relationship(
        "ExecutionAdapterVersion", back_populates="adapter"
    )


class ExecutionAdapterVersion(Base):
    __tablename__ = "execution_adapter_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    adapter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_adapters.id"), nullable=False, index=True
    )
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    adapter: Mapped["ExecutionAdapter"] = relationship(
        "ExecutionAdapter", back_populates="versions"
    )

    __table_args__ = (UniqueConstraint("adapter_id", "version_string", name="uq_adapter_version"),)


class Execution(Base, BaseMixin):
    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_status_created_at", "status", "created_at"),
        {"extend_existing": True},
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    benchmark_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("benchmark_versions.id"), nullable=False, index=True
    )
    submitted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization_members.id"), nullable=True, index=True
    )

    status: Mapped[ExecutionStatus] = mapped_column(
        ENUM(ExecutionStatus, name="execution_status"),
        nullable=False,
        default=ExecutionStatus.DRAFT,
    )

    target_model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    execution_config: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    benchmark_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Worker Tracking
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_requested: Mapped[bool] = mapped_column(default=False)

    # Progress Tracking
    total_items: Mapped[int] = mapped_column(default=0)
    completed_items: Mapped[int] = mapped_column(default=0)

    # Timing
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    model_outputs: Mapped[list["ModelOutput"]] = relationship(
        "ModelOutput", back_populates="execution"
    )
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="execution")


class ModelOutput(Base, BaseMixin):
    __tablename__ = "model_outputs"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_cases.id"), nullable=False, index=True
    )
    raw_output: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    execution: Mapped["Execution"] = relationship("Execution", back_populates="model_outputs")
    evaluation_result: Mapped["EvaluationResult"] = relationship(  # type: ignore
        "EvaluationResult", back_populates="model_output", uselist=False
    )


class Artifact(Base, BaseMixin):
    __tablename__ = "artifacts"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ArtifactType] = mapped_column(
        ENUM(ArtifactType, name="artifact_type"), nullable=False
    )
    uri: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    execution: Mapped["Execution"] = relationship("Execution", back_populates="artifacts")
