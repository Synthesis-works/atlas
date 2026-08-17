import uuid
from datetime import datetime

from pydantic import BaseModel

from packages.execution_engine.domain.models import ArtifactType, AttemptStatus, ExecutionState


class ArtifactResponse(BaseModel):
    id: uuid.UUID
    type: ArtifactType
    storage_uri: str


class ExecutionAttemptResponse(BaseModel):
    id: uuid.UUID
    attempt_number: int
    status: AttemptStatus
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    artifacts: list[ArtifactResponse]


class ExecutionResponse(BaseModel):
    id: uuid.UUID
    benchmark_version_id: uuid.UUID
    status: ExecutionState
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID
    max_retries: int
    total_items: int = 0
    completed_items: int = 0
    attempts: list[ExecutionAttemptResponse]


class ExecutionCreateRequest(BaseModel):
    pass


class ProjectExecutionListEntry(BaseModel):
    id: uuid.UUID
    benchmark_name: str
    target_model: str
    status: ExecutionState
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration: int | None = None
    total_items: int = 0
    completed_items: int = 0
    created_at: datetime


class ExecutionListResponse(BaseModel):
    items: list[ProjectExecutionListEntry]
    total: int
