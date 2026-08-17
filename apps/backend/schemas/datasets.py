import uuid
from datetime import datetime
from typing import Any

from atlas_db.models.dataset import DatasetLifecycle, DatasetStatus, DatasetExportState
from pydantic import BaseModel, ConfigDict


class DatasetBase(BaseModel):
    name: str
    description: str | None = None
    registry_id: uuid.UUID | None = None
    source_id: uuid.UUID | None = None
    license_id: uuid.UUID | None = None


class DatasetCreate(DatasetBase):
    pass


class DatasetRead(DatasetBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by_member_id: uuid.UUID | None
    status: DatasetStatus
    created_at: datetime
    updated_at: datetime

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
