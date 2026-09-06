"""Auth DTOs — field-for-field mirror of ``apps/backend/schemas/auth.py``."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    """Response body of ``POST /api/v1/auth/login``."""

    access_token: str
    token_type: str = "bearer"


class AuthUserRead(BaseModel):
    """Response body of ``GET /api/v1/auth/me`` and ``POST /api/v1/auth/register``."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    org_id: uuid.UUID | None = None
