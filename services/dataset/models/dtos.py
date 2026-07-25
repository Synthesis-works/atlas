from datetime import datetime
from typing import Any
from uuid import UUID

from atlas_db.models.dataset import DatasetLifecycle
from pydantic import BaseModel, ConfigDict


class DatasetRegistryDTO(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)


class DatasetSourceDTO(BaseModel):
    id: UUID
    name: str
    url: str | None = None
    type: str | None = None
    model_config = ConfigDict(from_attributes=True)


class DatasetLicenseDTO(BaseModel):
    id: UUID
    name: str
    url: str | None = None
    model_config = ConfigDict(from_attributes=True)


class DatasetDTO(BaseModel):
    id: UUID
    registry_id: UUID
    source_id: UUID
    license_id: UUID
    name: str
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)


class DatasetVersionDTO(BaseModel):
    id: UUID
    dataset_id: UUID
    version_string: str
    storage_path: str
    checksum: str | None = None
    validation_status: DatasetLifecycle
    schema_def: Any | None = None
    version_number: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DatasetRegistrationRequest(BaseModel):
    registry_id: UUID
    source_id: UUID
    license_id: UUID
    name: str
    description: str | None = None
