from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime
from atlas_db.models.dataset import ValidationStatus

class DatasetRegistryDTO(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class DatasetSourceDTO(BaseModel):
    id: UUID
    name: str
    url: Optional[str] = None
    type: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class DatasetLicenseDTO(BaseModel):
    id: UUID
    name: str
    url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class DatasetDTO(BaseModel):
    id: UUID
    registry_id: UUID
    source_id: UUID
    license_id: UUID
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class DatasetVersionDTO(BaseModel):
    id: UUID
    dataset_id: UUID
    version_string: str
    storage_path: str
    checksum: Optional[str] = None
    validation_status: ValidationStatus
    schema_def: Optional[Any] = None
    version_number: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DatasetRegistrationRequest(BaseModel):
    registry_id: UUID
    source_id: UUID
    license_id: UUID
    name: str
    description: Optional[str] = None
