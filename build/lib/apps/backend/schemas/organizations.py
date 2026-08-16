from datetime import datetime
from uuid import UUID

from atlas_db.models.core import InvitationStatus, MembershipStatus, OrganizationRole
from pydantic import BaseModel, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    display_name: str | None = Field(None, max_length=255)


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    slug: str
    display_name: str | None
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
    invited_by: UUID | None
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
