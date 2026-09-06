from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from atlas_db.models.dataset import DatasetLifecycle, DatasetStatus, DatasetExportState
from pydantic import BaseModel, ConfigDict, Field


class DatasetBase(BaseModel):
    name: str
    description: str | None = None
    registry_id: uuid.UUID | None = None
    source_id: uuid.UUID | None = None
    license_id: uuid.UUID | None = None


class DatasetCreate(DatasetBase):
    version_string: str = Field(default="v1.0.0")
    tasks: list[DatasetTaskItem] = Field(default_factory=list)


class DatasetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    registry_id: uuid.UUID | None = None
    source_id: uuid.UUID | None = None
    license_id: uuid.UUID | None = None


class DatasetTaskItem(BaseModel):
    """A single dataset task authored by the agent/CLI via REST.

    ``input``/``expected_output`` are required; ``description`` is optional.
    """

    input: Any
    expected_output: Any
    description: str | None = None


class DatasetTaskUpload(BaseModel):
    """Upload (replace) tasks for a dataset as a fresh version."""

    tasks: list[DatasetTaskItem]
    version_string: str = "v1.0.0"


class DatasetRead(DatasetBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by_member_id: uuid.UUID | None
    status: DatasetStatus
    created_at: datetime
    updated_at: datetime
    versions: list[DatasetVersionRead] | None = None
    total_tasks: int = 0
    sample_tasks: list[Any] = []

    model_config = ConfigDict(from_attributes=True)


class DatasetVersionBase(BaseModel):
    version_string: str
    storage_path: str
    checksum: str | None = None
    schema_def: dict[str, Any] | list[Any] | None = None


class DatasetVersionCreate(DatasetVersionBase):
    pass


class DatasetVersionRead(DatasetVersionBase):
    id: uuid.UUID
    dataset_id: uuid.UUID
    lifecycle: DatasetLifecycle
    version_number: int
    created_at: datetime
    created_by_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)


class DatasetValidationResult(BaseModel):
    dataset_id: uuid.UUID
    version_id: uuid.UUID | None = None
    lifecycle: DatasetLifecycle
    valid: bool
    task_count: int = 0
    messages: list[str] = []


class DatasetExportResponse(BaseModel):
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    project_id: uuid.UUID
    status: DatasetExportState
    error_message: str | None = None
    artifact_uri: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)
