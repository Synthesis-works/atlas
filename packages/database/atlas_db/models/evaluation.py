import uuid
import enum
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import String, ForeignKey, DateTime, Float, Enum as SQLEnum, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from atlas_db.core.base import Base

def utcnow():
    return datetime.now(timezone.utc)


class EvaluationJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

class AttemptStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class MetricCategory(str, enum.Enum):
    CORRECTNESS = "CORRECTNESS"
    PERFORMANCE = "PERFORMANCE"
    EFFICIENCY = "EFFICIENCY"
    SAFETY = "SAFETY"
    QUALITY = "QUALITY"
    COST = "COST"

class MetricDirection(str, enum.Enum):
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    LOWER_IS_BETTER = "LOWER_IS_BETTER"
    NEUTRAL = "NEUTRAL"


# -------------------------------------------------------------------
# CORE EVALUATION
# -------------------------------------------------------------------

class EvaluationJob(Base):
    __tablename__ = "evaluation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    atlas_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[EvaluationJobStatus] = mapped_column(SQLEnum(EvaluationJobStatus), default=EvaluationJobStatus.PENDING, nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    attempts: Mapped[List["EvaluationAttempt"]] = relationship("EvaluationAttempt", back_populates="job", cascade="all, delete-orphan")


class EvaluationAttempt(Base):
    __tablename__ = "evaluation_attempts"
    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="uq_eval_attempt_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_pipeline_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(SQLEnum(AttemptStatus), default=AttemptStatus.QUEUED, nullable=False, index=True)
    
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["EvaluationJob"] = relationship("EvaluationJob", back_populates="attempts")
    pipeline_version: Mapped["EvaluationPipelineVersion"] = relationship("EvaluationPipelineVersion")
    artifacts: Mapped[List["EvaluationArtifact"]] = relationship("EvaluationArtifact", back_populates="attempt", cascade="all, delete-orphan")
    result: Mapped[Optional["EvaluationResult"]] = relationship("EvaluationResult", back_populates="attempt", uselist=False, cascade="all, delete-orphan")


# -------------------------------------------------------------------
# PIPELINES
# -------------------------------------------------------------------

class EvaluationPipeline(Base):
    __tablename__ = "evaluation_pipelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    versions: Mapped[List["EvaluationPipelineVersion"]] = relationship("EvaluationPipelineVersion", back_populates="pipeline", cascade="all, delete-orphan")


class EvaluationPipelineVersion(Base):
    __tablename__ = "evaluation_pipeline_versions"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "version", name="uq_eval_pipeline_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_pipelines.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    config_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    pipeline: Mapped["EvaluationPipeline"] = relationship("EvaluationPipeline", back_populates="versions")


# -------------------------------------------------------------------
# JUDGES
# -------------------------------------------------------------------

class Judge(Base):
    __tablename__ = "judges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    versions: Mapped[List["JudgeVersion"]] = relationship("JudgeVersion", back_populates="judge", cascade="all, delete-orphan")


class JudgeVersion(Base):
    __tablename__ = "judge_versions"
    __table_args__ = (
        UniqueConstraint("judge_id", "version", name="uq_judge_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("judges.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)

    judge: Mapped["Judge"] = relationship("Judge", back_populates="versions")


class JudgeTrace(Base):
    __tablename__ = "judge_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False)
    judge_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("judge_versions.id", ondelete="RESTRICT"), nullable=False)
    
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    response: Mapped[str] = mapped_column(String, nullable=False)
    rubric: Mapped[str] = mapped_column(String, nullable=False)
    reasoning: Mapped[str] = mapped_column(String, nullable=False)
    
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    result: Mapped["EvaluationResult"] = relationship("EvaluationResult", back_populates="judge_traces")


# -------------------------------------------------------------------
# ARTIFACTS & RESULTS
# -------------------------------------------------------------------

class EvaluationArtifact(Base):
    __tablename__ = "evaluation_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_attempts.id", ondelete="CASCADE"), nullable=False)
    
    artifact_hash: Mapped[str] = mapped_column(String, nullable=False)
    target_output: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reference_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    attempt: Mapped["EvaluationAttempt"] = relationship("EvaluationAttempt", back_populates="artifacts")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_attempts.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    artifacts_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    attempt: Mapped["EvaluationAttempt"] = relationship("EvaluationAttempt", back_populates="result")
    metrics: Mapped[List["MetricValue"]] = relationship("MetricValue", back_populates="result", cascade="all, delete-orphan")
    judge_traces: Mapped[List["JudgeTrace"]] = relationship("JudgeTrace", back_populates="result", cascade="all, delete-orphan")


# -------------------------------------------------------------------
# METRICS
# -------------------------------------------------------------------

class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_metric_definition_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False, default="1.0")
    category: Mapped[MetricCategory] = mapped_column(SQLEnum(MetricCategory), nullable=False)
    direction: Mapped[MetricDirection] = mapped_column(SQLEnum(MetricDirection), nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)


class MetricValue(Base):
    __tablename__ = "metric_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False)
    metric_def_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("metric_definitions.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    normalized_value: Mapped[float] = mapped_column(Float, nullable=False)
    
    source: Mapped[str] = mapped_column(String, nullable=False, index=True)
    aggregation: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    result: Mapped["EvaluationResult"] = relationship("EvaluationResult", back_populates="metrics")
    definition: Mapped["MetricDefinition"] = relationship("MetricDefinition")


# -------------------------------------------------------------------
# CAPABILITY
# -------------------------------------------------------------------

class CapabilityDefinition(Base):
    __tablename__ = "capability_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class CapabilityProfile(Base):
    __tablename__ = "capability_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    adapter_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    scores: Mapped[List["CapabilityScore"]] = relationship("CapabilityScore", back_populates="profile", cascade="all, delete-orphan")


class CapabilityScore(Base):
    __tablename__ = "capability_scores"
    __table_args__ = (
        UniqueConstraint("profile_id", "capability_definition_id", name="uq_capability_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("capability_profiles.id", ondelete="CASCADE"), nullable=False)
    capability_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("capability_definitions.id", ondelete="RESTRICT"), nullable=False)
    
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    profile: Mapped["CapabilityProfile"] = relationship("CapabilityProfile", back_populates="scores")
    definition: Mapped["CapabilityDefinition"] = relationship("CapabilityDefinition")
