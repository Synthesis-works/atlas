from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from atlas_db.models.core import OrganizationRole, MembershipStatus, InvitationStatus

class OrganizationCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)

class OrganizationRead(BaseModel):
    id: UUID
    name: str
    slug: str
    display_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class OrganizationMemberRead(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: OrganizationRole
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class InvitationCreate(BaseModel):
    email: EmailStr
    role: OrganizationRole = OrganizationRole.MEMBER

class InvitationRead(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    role: OrganizationRole
    status: InvitationStatus
    invited_by: Optional[UUID]
    expires_at: datetime
    accepted_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
