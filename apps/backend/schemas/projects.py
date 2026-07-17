from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    description: Optional[str] = None

class ProjectRead(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    org_id: Optional[UUID]
    created_by_member_id: Optional[UUID]
    updated_by_member_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
