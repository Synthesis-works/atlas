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
    run_id: uuid.UUID
    task_id: uuid.UUID
    worker_id: uuid.UUID | None
    status: str
    target_model: str | None = None
    started_at: datetime | None
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
    attempts: list[ExecutionAttemptResponse]


class ExecutionCreateRequest(BaseModel):
    # Benchmark version ID goes in the path usually, but this is the request body?
    # Actually, path is /benchmarks/{id}/executions. No body is strictly required,
    # but maybe we can allow passing config here.
    # We will just use an empty body for now.
    pass


class ExecutionListResponse(BaseModel):
    items: list[ExecutionResponse]
    total: int
