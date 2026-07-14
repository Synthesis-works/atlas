import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ENUM

from atlas_db.core.base import Base, BaseMixin

class RunStatus(PyEnum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    ABORTING = "ABORTING"
    CANCELLED = "CANCELLED"

class TaskStatus(PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class WorkerStatus(PyEnum):
    REGISTERED = "REGISTERED"
    READY = "READY"
    BUSY = "BUSY"
    UNHEALTHY = "UNHEALTHY"
    OFFLINE = "OFFLINE"

class EventType(PyEnum):
    RUN_CREATED = "RUN_CREATED"
    RUN_VALIDATED = "RUN_VALIDATED"
    RUN_QUEUED = "RUN_QUEUED"
    RUN_STARTED = "RUN_STARTED"
    RUN_PAUSED = "RUN_PAUSED"
    RUN_RESUMED = "RUN_RESUMED"
    RUN_FAILED = "RUN_FAILED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_CANCELLED = "RUN_CANCELLED"
    TASK_QUEUED = "TASK_QUEUED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    WORKER_HEARTBEAT = "WORKER_HEARTBEAT"
    WORKER_REGISTERED = "WORKER_REGISTERED"
    WORKER_OFFLINE = "WORKER_OFFLINE"
    WORKER_LOST = "WORKER_LOST"
    TASK_SCHEDULED = "TASK_SCHEDULED"
    TASK_DEFERRED = "TASK_DEFERRED"
    TASK_REJECTED_BY_POLICY = "TASK_REJECTED_BY_POLICY"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    TASK_REQUEUED = "TASK_REQUEUED"
    RUN_TIMEOUT = "RUN_TIMEOUT"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    RECOVERY_SKIPPED = "RECOVERY_SKIPPED"

class ArtifactType(PyEnum):
    LOG = "LOG"
    TRACE = "TRACE"
    OUTPUT = "OUTPUT"

class ExecutionAdapter(Base, BaseMixin):
    __tablename__ = "execution_adapters"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    
    versions: Mapped[list["ExecutionAdapterVersion"]] = relationship("ExecutionAdapterVersion", back_populates="adapter", cascade="all, delete-orphan")

class ExecutionAdapterVersion(Base, BaseMixin):
    __tablename__ = "execution_adapter_versions"
    
    adapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_adapters.id", ondelete="CASCADE"), nullable=False, index=True)
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    image_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    entrypoint: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    default_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    adapter: Mapped["ExecutionAdapter"] = relationship("ExecutionAdapter", back_populates="versions")

class ExecutionWorker(Base, BaseMixin):
    __tablename__ = "execution_workers"
    
    adapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_adapters.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[WorkerStatus] = mapped_column(
        ENUM(WorkerStatus, name="worker_status"), 
        default=WorkerStatus.REGISTERED,
        nullable=False
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hardware_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_load: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    health: Mapped[str | None] = mapped_column(String(50), nullable=True)

class EvaluationSession(Base, BaseMixin):
    __tablename__ = "evaluation_sessions"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    atlas_runs: Mapped[list["AtlasRun"]] = relationship("AtlasRun", back_populates="session", cascade="all, delete-orphan")

class AtlasRun(Base, BaseMixin):
    __tablename__ = "atlas_runs"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    benchmark_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("benchmark_versions.id"), nullable=False, index=True)
    adapter_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_adapter_versions.id"), nullable=False, index=True)
    target_model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    status: Mapped[RunStatus] = mapped_column(
        ENUM(RunStatus, name="run_status"),
        nullable=False,
        default=RunStatus.CREATED
    )
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Progress Tracking fields (Slice 3B)
    total_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    running_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    session: Mapped["EvaluationSession"] = relationship("EvaluationSession", back_populates="atlas_runs")
    tasks: Mapped[list["AtlasTask"]] = relationship("AtlasTask", back_populates="run", cascade="all, delete-orphan")
    model_outputs: Mapped[list["ModelOutput"]] = relationship("ModelOutput", back_populates="atlas_run", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="atlas_run", cascade="all, delete-orphan")
    events: Mapped[list["RunEvent"]] = relationship("RunEvent", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_atlas_runs_status_created_at", "status", "created_at"),
    )

class AtlasTask(Base, BaseMixin):
    __tablename__ = "atlas_tasks"

    atlas_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atlas_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"), nullable=False, index=True)
    assigned_worker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("execution_workers.id", ondelete="SET NULL"), nullable=True, index=True)
    
    status: Mapped[TaskStatus] = mapped_column(
        ENUM(TaskStatus, name="task_status"), 
        nullable=False,
        default=TaskStatus.PENDING
    )
    
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    retryable: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)
    
    run: Mapped["AtlasRun"] = relationship("AtlasRun", back_populates="tasks")
    worker: Mapped["ExecutionWorker"] = relationship("ExecutionWorker")
    model_output: Mapped["ModelOutput"] = relationship("ModelOutput", back_populates="task", uselist=False)

class ModelOutput(Base, BaseMixin):
    __tablename__ = "model_outputs"

    atlas_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atlas_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"), nullable=False, index=True)
    atlas_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("atlas_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    
    raw_output: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    atlas_run: Mapped["AtlasRun"] = relationship("AtlasRun", back_populates="model_outputs")
    task: Mapped["AtlasTask"] = relationship("AtlasTask", back_populates="model_output")

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

class RunEvent(Base, BaseMixin):
    __tablename__ = "run_events"
    
    atlas_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("atlas_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    atlas_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("atlas_tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    execution_worker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("execution_workers.id", ondelete="SET NULL"), nullable=True, index=True)
    
    type: Mapped[EventType] = mapped_column(
        ENUM(EventType, name="event_type"), 
        nullable=False, 
        index=True
    )
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    
    run: Mapped["AtlasRun"] = relationship("AtlasRun", back_populates="events")
