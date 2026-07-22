import uuid

from pydantic import BaseModel

from packages.execution_engine.domain.models import ArtifactType


class AcquireRequest(BaseModel):
    worker_id: uuid.UUID
    capabilities: list[str]


class AcquireResponse(BaseModel):
    lease_id: uuid.UUID
    execution_id: uuid.UUID
    attempt_id: uuid.UUID
    heartbeat_interval_seconds: int
    lease_duration_seconds: int
    benchmark_version_id: uuid.UUID
    # config/artifact_upload config could go here


class HeartbeatRequest(BaseModel):
    worker_id: uuid.UUID


class HeartbeatResponse(BaseModel):
    execution_id: uuid.UUID
    lease_expires_at: str


class ArtifactDTO(BaseModel):
    type: ArtifactType
    storage_uri: str


class CompleteSuccessRequest(BaseModel):
    worker_id: uuid.UUID
    artifacts: list[ArtifactDTO]


class CompleteFailureRequest(BaseModel):
    worker_id: uuid.UUID
    error_message: str
    artifacts: list[ArtifactDTO]
