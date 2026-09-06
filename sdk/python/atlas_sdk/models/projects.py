"""Project/Organization DTOs — field-for-field mirror of the backend schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ProjectRead(BaseModel):
    """Single project summary from ``GET /api/v1/organizations/{org_id}/projects``."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    org_id: uuid.UUID | None = None


class OrganizationRead(BaseModel):
    """Single organization summary from ``GET /api/v1/organizations``."""

    id: uuid.UUID
    name: str
    slug: str
    display_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
