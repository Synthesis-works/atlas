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
