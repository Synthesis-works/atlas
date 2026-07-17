from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime

from atlas_db.models.dataset import DatasetStatus, DatasetLifecycle

class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None
    registry_id: Optional[uuid.UUID] = None
    source_id: Optional[uuid.UUID] = None
    license_id: Optional[uuid.UUID] = None

class DatasetCreate(DatasetBase):
    pass

class DatasetRead(DatasetBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by_member_id: Optional[uuid.UUID]
    status: DatasetStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetVersionBase(BaseModel):
    version_string: str
    storage_path: str
    checksum: Optional[str] = None
    schema_def: Optional[Union[Dict[str, Any], List[Any]]] = None

class DatasetVersionCreate(DatasetVersionBase):
    pass

class DatasetVersionRead(DatasetVersionBase):
    id: uuid.UUID
    dataset_id: uuid.UUID
    lifecycle: DatasetLifecycle
    version_number: int
    created_at: datetime
    created_by_id: Optional[uuid.UUID]

    model_config = ConfigDict(from_attributes=True)
