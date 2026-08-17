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
    target_model: str = "gemini-2.5-flash"
    completed_items: int = 0
    total_items: int = 1
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID
    max_retries: int
    attempts: list[ExecutionAttemptResponse] = []


class ExecutionCreateRequest(BaseModel):
    target_model: str = "gemini-2.5-flash"
    dataset_version_id: uuid.UUID | None = None
    execution_config: dict | None = None


class DispatchTargetResponse(BaseModel):
    benchmark_version_id: uuid.UUID
    benchmark_name: str
    version_string: str
    dataset_version_id: uuid.UUID | None = None


class ExecutionListResponse(BaseModel):
    items: list[ExecutionResponse]
    total: int
