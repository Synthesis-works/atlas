import uuid

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    password: str = Field(
        ..., min_length=8, description="User's password, must be at least 8 characters"
    )


class UserLogin(BaseModel):
    email: str | None = Field(default=None, description="User's email address")
    username: str | None = Field(default=None, description="User's username")
    identifier: str | None = Field(default=None, description="User's username or email")
    password: str = Field(..., description="User's password")

    @property
    def login_identifier(self) -> str:
        return (self.email or self.username or self.identifier or "").strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenClaims(BaseModel):
    sub: uuid.UUID
    membership_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    exp: int
    iat: int
    jti: uuid.UUID


class AuthUserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    org_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}
