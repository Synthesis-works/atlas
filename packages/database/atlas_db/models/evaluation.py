import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from atlas_db.core.base import Base, BaseMixin, utcnow

class StrategyType(str, enum.Enum):
    EXACT_MATCH = "exact_match"
    LLM_JUDGE = "llm_judge"
    SCRIPT = "script"

class EvaluationStatus(str, enum.Enum):
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"

class EvaluationStrategy(Base, BaseMixin):
    __tablename__ = "evaluation_strategies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    type: Mapped[StrategyType] = mapped_column(
        ENUM(StrategyType, name="strategy_type"),
        nullable=False
    )

    versions: Mapped[list["EvaluationStrategyVersion"]] = relationship("EvaluationStrategyVersion", back_populates="strategy")

class EvaluationStrategyVersion(Base):
    __tablename__ = "evaluation_strategy_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_strategies.id"), nullable=False, index=True)
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    parameters: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    strategy: Mapped["EvaluationStrategy"] = relationship("EvaluationStrategy", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("strategy_id", "version_string", name="uq_strategy_version"),
    )

class Judge(Base, BaseMixin):
    __tablename__ = "judges"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    model_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_template: Mapped[str] = mapped_column(String, nullable=False)

    organization: Mapped["Organization | None"] = relationship("Organization")

class EvaluationResult(Base, BaseMixin):
    __tablename__ = "evaluation_results"

    model_output_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_outputs.id", ondelete="CASCADE"), nullable=False, unique=True)
    strategy_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_strategy_versions.id"), nullable=False, index=True)
    judge_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("judges.id"), nullable=True, index=True)
    
    status: Mapped[EvaluationStatus] = mapped_column(
        ENUM(EvaluationStatus, name="evaluation_status", create_type=False),
        nullable=False,
        default=EvaluationStatus.COMPLETED
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_measurements: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(String, nullable=True)
    warnings: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    failure_reasons: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    evaluation_context: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    model_output: Mapped["ModelOutput"] = relationship("ModelOutput", back_populates="evaluation_result")
    strategy_version: Mapped["EvaluationStrategyVersion"] = relationship("EvaluationStrategyVersion")
    judge: Mapped["Judge | None"] = relationship("Judge")
    details: Mapped["EvaluationResultDetail | None"] = relationship("EvaluationResultDetail", back_populates="evaluation_result", uselist=False)
    artifacts: Mapped[list["EvaluationArtifact"]] = relationship("EvaluationArtifact", back_populates="evaluation_result")

class CapabilityProfile(Base, BaseMixin):
    __tablename__ = "capability_profiles"

    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_strategy_versions.id"), nullable=False, index=True)
    profile_version: Mapped[int] = mapped_column(nullable=False, default=1)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_explanation: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    profile_metadata: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    evaluation: Mapped["EvaluationResult"] = relationship("EvaluationResult")
    strategy_version: Mapped["EvaluationStrategyVersion"] = relationship("EvaluationStrategyVersion")
    scores: Mapped[list["CapabilityScore"]] = relationship("CapabilityScore", back_populates="profile")

class CapabilityScore(Base, BaseMixin):
    __tablename__ = "capability_scores"

    capability_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("capability_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    capability_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("capabilities.id"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)

    profile: Mapped["CapabilityProfile"] = relationship("CapabilityProfile", back_populates="scores")

class EvaluationResultDetail(Base):
    __tablename__ = "evaluation_result_details"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evaluation_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False, unique=True)
    judge_outputs: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    evaluation_logs: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    evaluation_result: Mapped["EvaluationResult"] = relationship("EvaluationResult", back_populates="details")

class EvaluationArtifact(Base, BaseMixin):
    __tablename__ = "evaluation_artifacts"

    evaluation_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=True)

    evaluation_result: Mapped["EvaluationResult"] = relationship("EvaluationResult", back_populates="artifacts")

