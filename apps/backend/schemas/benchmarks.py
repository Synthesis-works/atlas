from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class BenchmarkCreate(BaseModel):
    name: str = Field(..., max_length=255)
    objective: Optional[str] = None
    category_ids: Optional[List[UUID]] = []
    capability_ids: Optional[List[UUID]] = []

class BenchmarkUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    objective: Optional[str] = None
    category_ids: Optional[List[UUID]] = None
    capability_ids: Optional[List[UUID]] = None

class BenchmarkRead(BaseModel):
    id: UUID
    project_id: UUID
    state: str
    name: str

    class Config:
        from_attributes = True

class BenchmarkVersionCreate(BaseModel):
    version_string: str
    dataset_version_ids: Optional[List[UUID]] = []
    evaluation_strategy_id: Optional[UUID] = None

class BenchmarkVersionUpdate(BaseModel):
    dataset_version_ids: Optional[List[UUID]] = None
    evaluation_strategy_id: Optional[UUID] = None

class BenchmarkVersionRead(BaseModel):
    id: UUID
    benchmark_id: UUID
    version_string: str
    state: str
    dataset_version_ids: Optional[List[UUID]] = []
    evaluation_strategy_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True
