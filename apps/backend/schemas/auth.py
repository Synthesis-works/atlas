from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid

class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    password: str = Field(..., min_length=8, description="User's password, must be at least 8 characters")

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenClaims(BaseModel):
    sub: uuid.UUID
    membership_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    exp: int
    iat: int
    jti: uuid.UUID

class AuthUserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    org_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}
