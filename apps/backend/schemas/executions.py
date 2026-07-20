from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID
from atlas_db.models.execution import ExecutionStatus, ArtifactType

class ArtifactBase(BaseModel):
    type: ArtifactType
    uri: str
    size_bytes: Optional[int] = None

class ArtifactResponse(ArtifactBase):
    id: UUID
    execution_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ExecutionCreate(BaseModel):
    benchmark_version_id: UUID = Field(..., description="The ID of the benchmark version to execute.")
    target_model: str = Field(..., description="The target model to evaluate.")
    execution_config: Optional[Dict[str, Any]] = Field(default=None, description="Configuration for the execution.")

class ExecutionResponse(BaseModel):
    id: UUID
    project_id: UUID
    benchmark_version_id: UUID
    submitted_by_id: Optional[UUID]
    status: ExecutionStatus
    target_model: str
    execution_config: Optional[Dict[str, Any]]
    benchmark_hash: Optional[str]
    cancellation_requested: bool
    total_items: int = 0
    completed_items: int = 0
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ExecutionUpdate(BaseModel):
    # Only internal services should transition statuses typically, but this is a stub for API
    pass
