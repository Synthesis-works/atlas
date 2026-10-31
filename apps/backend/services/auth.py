import uuid
from datetime import UTC, datetime, timedelta

import jwt
from atlas_db.models.core import User
from atlas_db.repositories.core import UserRepository
from fastapi import HTTPException, status
from pwdlib import PasswordHash

from apps.backend.config import settings
from apps.backend.schemas.auth import TokenResponse, UserLogin, UserRegister

# Initialize Argon2 password hasher
password_hash = PasswordHash.recommended()

# Verified against when no user exists so failed logins take a similar amount of
# time whether or not the email is registered. The password is irrelevant.
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$ORUH2NfJM3zgarHDCpuChg"
    "$QkFH9uFe4eJlzMtq/3v2jxkNxSmFuMlG54Y3/3PuI3g"
)

_INVALID_CREDENTIALS = "Invalid email or password"


def _invalid_credentials() -> HTTPException:
    """A single generic failure for every credential problem."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_INVALID_CREDENTIALS,
        headers={"WWW-Authenticate": "Bearer"},
    )


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def hash_password(self, password: str) -> str:
        return password_hash.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return password_hash.verify(plain_password, hashed_password)

    def create_access_token(self, user: User, membership_id: uuid.UUID | None = None) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_expire_minutes)
        to_encode = {
            "sub": str(user.id),
            "membership_id": str(membership_id) if membership_id else None,
            "organization_id": str(user.org_id) if user.org_id else None,
            "exp": expire,
            "iat": datetime.now(UTC),
            "jti": str(uuid.uuid4()),
        }
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    def register_user(self, data: UserRegister) -> User:
        email = str(data.email).strip().lower()
        existing_user = self.user_repo.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists"
            )

        user_data = {
            "email": email,
            "full_name": data.full_name.strip(),
            "password_hash": self.hash_password(data.password),
            "is_active": True,
            "is_verified": False,
        }
        user = self.user_repo.create(user_data)
        return user

    def authenticate_user(self, data: UserLogin) -> TokenResponse:
        email = str(data.email).strip().lower()
        user = self.user_repo.get_by_email(email)

        if user is None or not user.password_hash:
            # Burn comparable time for unknown accounts, then fail identically.
            self.verify_password(data.password, _DUMMY_PASSWORD_HASH)
            raise _invalid_credentials()

        if not self.verify_password(data.password, user.password_hash):
            raise _invalid_credentials()

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
            )

        access_token = self.create_access_token(user)
        return TokenResponse(access_token=access_token)
