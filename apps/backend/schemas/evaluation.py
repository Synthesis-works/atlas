import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CapabilityScoreRead(BaseModel):
    id: uuid.UUID
    capability_profile_id: uuid.UUID
    capability_id: uuid.UUID
    score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CapabilityProfileRead(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    overall_score: float | None = None
    profile_metadata: dict[str, Any] | None = None
    scores: list[CapabilityScoreRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvaluationResultRead(BaseModel):
    id: uuid.UUID
    model_output_id: uuid.UUID
    strategy_version_id: uuid.UUID
    judge_id: uuid.UUID | None = None
    passed: bool
    confidence: float | None = None
    raw_measurements: dict[str, Any] | None = None
    reasoning: str | None = None
    warnings: dict[str, Any] | None = None
    failure_reasons: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvaluationSummaryResponse(BaseModel):
    execution_id: uuid.UUID
    total_outputs: int
    evaluated_outputs: int
    passed_outputs: int
    profile: CapabilityProfileRead | None = None

    model_config = {"from_attributes": True}
