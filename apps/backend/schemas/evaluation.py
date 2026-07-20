import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
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
    overall_score: Optional[float] = None
    profile_metadata: Optional[Dict[str, Any]] = None
    scores: List[CapabilityScoreRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class EvaluationResultRead(BaseModel):
    id: uuid.UUID
    model_output_id: uuid.UUID
    strategy_version_id: uuid.UUID
    judge_id: Optional[uuid.UUID] = None
    passed: bool
    confidence: Optional[float] = None
    raw_measurements: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    warnings: Optional[Dict[str, Any]] = None
    failure_reasons: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class EvaluationSummaryResponse(BaseModel):
    execution_id: uuid.UUID
    total_outputs: int
    evaluated_outputs: int
    passed_outputs: int
    profile: Optional[CapabilityProfileRead] = None

    model_config = {"from_attributes": True}
