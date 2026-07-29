from datetime import datetime
from typing import Any
from uuid import UUID

from atlas_db.models.execution import ArtifactType, ExecutionStatus
from pydantic import BaseModel, ConfigDict, Field


class ArtifactBase(BaseModel):
    type: ArtifactType
    uri: str
    size_bytes: int | None = None


class ArtifactResponse(ArtifactBase):
    id: UUID
    execution_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionCreate(BaseModel):
    benchmark_version_id: UUID = Field(
        ..., description="The ID of the benchmark version to execute."
    )
    target_model: str = Field(..., description="The target model to evaluate.")
    execution_config: dict[str, Any] | None = Field(
        default=None, description="Configuration for the execution."
    )


class ExecutionResponse(BaseModel):
    id: UUID
    project_id: UUID
    benchmark_version_id: UUID
    submitted_by_id: UUID | None
    status: ExecutionStatus
    target_model: str
    execution_config: dict[str, Any] | None
    benchmark_hash: str | None
    cancellation_requested: bool
    total_items: int = 0
    completed_items: int = 0
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionUpdate(BaseModel):
    # Only internal services should transition statuses typically, but this is a stub for API
    pass


class ExecutionHistoryRead(BaseModel):
    id: UUID
    benchmark_name: str
    target_model: str
    status: ExecutionStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration: int | None = (
        None  # in milliseconds or seconds, depending on how we calculate it (or we could omit and let the client calculate)
    )
    project_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ModelActivityRead(BaseModel):
    name: str
    last_executed_at: datetime
    execution_count: int

    model_config = ConfigDict(from_attributes=True)
