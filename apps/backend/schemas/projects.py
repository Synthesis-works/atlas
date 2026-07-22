from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    description: str | None = None


class ProjectRead(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    org_id: UUID | None
    created_by_member_id: UUID | None
    updated_by_member_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
