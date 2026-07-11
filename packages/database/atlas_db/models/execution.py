import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer, BigInteger, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from atlas_db.core.base import Base, BaseMixin, utcnow

class AdapterType(str, enum.Enum):
    LOCAL = "local"
    KUBERNETES = "kubernetes"
    AWS_BATCH = "aws_batch"

class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ArtifactType(str, enum.Enum):
    LOG = "log"
    WEIGHTS = "weights"
    FILE = "file"

class ExecutionAdapter(Base, BaseMixin):
    __tablename__ = "execution_adapters"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    type: Mapped[AdapterType] = mapped_column(
        ENUM(AdapterType, name="adapter_type"),
        nullable=False
    )

    versions: Mapped[list["ExecutionAdapterVersion"]] = relationship("ExecutionAdapterVersion", back_populates="adapter")

class ExecutionAdapterVersion(Base):
    __tablename__ = "execution_adapter_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    adapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_adapters.id"), nullable=False, index=True)
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    adapter: Mapped["ExecutionAdapter"] = relationship("ExecutionAdapter", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("adapter_id", "version_string", name="uq_adapter_version"),
    )

class EvaluationSession(Base, BaseMixin):
    __tablename__ = "evaluation_sessions"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    atlas_runs: Mapped[list["AtlasRun"]] = relationship("AtlasRun", back_populates="session")

class AtlasRun(Base, BaseMixin):
    __tablename__ = "atlas_runs"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_sessions.id"), nullable=False, index=True)
    benchmark_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("benchmark_versions.id"), nullable=False, index=True)
    adapter_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_adapter_versions.id"), nullable=False, index=True)
    target_model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[RunStatus] = mapped_column(
        ENUM(RunStatus, name="run_status"),
        nullable=False,
        default=RunStatus.PENDING
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["EvaluationSession"] = relationship("EvaluationSession", back_populates="atlas_runs")
    model_outputs: Mapped[list["ModelOutput"]] = relationship("ModelOutput", back_populates="atlas_run")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="atlas_run")

    __table_args__ = (
        Index("ix_atlas_runs_status_created_at", "status", "created_at"),
    )

class ModelOutput(Base, BaseMixin):
    __tablename__ = "model_outputs"

    atlas_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atlas_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"), nullable=False, index=True)
    raw_output: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    atlas_run: Mapped["AtlasRun"] = relationship("AtlasRun", back_populates="model_outputs")
    evaluation_result: Mapped["EvaluationResult"] = relationship("EvaluationResult", back_populates="model_output", uselist=False)

class Artifact(Base, BaseMixin):
    __tablename__ = "artifacts"

    atlas_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atlas_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[ArtifactType] = mapped_column(
        ENUM(ArtifactType, name="artifact_type"),
        nullable=False
    )
    uri: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    atlas_run: Mapped["AtlasRun"] = relationship("AtlasRun", back_populates="artifacts")
