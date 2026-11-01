"""Service-level tests for authentication hardening.

Covers email-only login, normalization, generic credential errors, disabled
accounts, and registration normalization against a real (in-memory) database.
"""

import pytest
from atlas_db.repositories.core import UserRepository
from fastapi import HTTPException
from pydantic import ValidationError

from apps.backend.schemas.auth import UserLogin, UserRegister
from apps.backend.services.auth import AuthService


@pytest.fixture
def auth_service(db_session) -> AuthService:
    return AuthService(UserRepository(db_session))


def _create_user(
    auth_service: AuthService,
    *,
    email: str = "User@Example.com",
    password: str = "supersecret",
    is_active: bool = True,
):
    return auth_service.user_repo.create(
        {
            "email": email,
            "full_name": "Test User",
            "password_hash": auth_service.hash_password(password),
            "is_active": is_active,
            "is_verified": True,
        }
    )


def test_register_normalizes_email_and_name(auth_service: AuthService):
    user = auth_service.register_user(
        UserRegister(email="  User@Example.COM ", full_name="  Jane Doe  ", password="supersecret")
    )

    assert user.email == "user@example.com"
    assert user.full_name == "Jane Doe"
    assert user.is_active is True
    assert user.password_hash != "supersecret"
    assert auth_service.verify_password("supersecret", user.password_hash)


def test_register_rejects_duplicate_email_case_insensitively(auth_service: AuthService):
    auth_service.register_user(
        UserRegister(email="user@example.com", full_name="Jane Doe", password="supersecret")
    )

    with pytest.raises(HTTPException) as excinfo:
        auth_service.register_user(
            UserRegister(email="USER@EXAMPLE.COM", full_name="Other Name", password="supersecret")
        )

    assert excinfo.value.status_code == 409


def test_authenticate_accepts_case_insensitive_email(auth_service: AuthService):
    _create_user(auth_service)

    token = auth_service.authenticate_user(
        UserLogin(email=" USER@EXAMPLE.COM ", password="supersecret")
    )

    assert token.token_type == "bearer"
    assert token.access_token.count(".") == 2


def test_authenticate_returns_identical_generic_error_for_unknown_and_wrong_password(
    auth_service: AuthService,
):
    _create_user(auth_service, email="known@example.com", password="supersecret")

    with pytest.raises(HTTPException) as unknown_exc:
        auth_service.authenticate_user(
            UserLogin(email="nobody@example.com", password="supersecret")
        )

    with pytest.raises(HTTPException) as wrong_exc:
        auth_service.authenticate_user(
            UserLogin(email="known@example.com", password="wrong-password")
        )

    assert unknown_exc.value.status_code == 401
    assert wrong_exc.value.status_code == 401
    assert unknown_exc.value.detail == "Invalid email or password"
    assert unknown_exc.value.detail == wrong_exc.value.detail


def test_authenticate_checks_password_before_revealing_disabled_account(
    auth_service: AuthService,
):
    _create_user(
        auth_service, email="disabled@example.com", password="supersecret", is_active=False
    )

    # Wrong password must not disclose that the account is disabled.
    with pytest.raises(HTTPException) as wrong_exc:
        auth_service.authenticate_user(
            UserLogin(email="disabled@example.com", password="wrong-password")
        )
    assert wrong_exc.value.status_code == 401

    with pytest.raises(HTTPException) as disabled_exc:
        auth_service.authenticate_user(
            UserLogin(email="disabled@example.com", password="supersecret")
        )
    assert disabled_exc.value.status_code == 403


def test_unknown_email_still_runs_a_dummy_password_verification(
    auth_service: AuthService, monkeypatch: pytest.MonkeyPatch
):
    seen_hashes: list[str] = []
    real_verify = auth_service.verify_password

    def recording_verify(plain: str, hashed: str) -> bool:
        seen_hashes.append(hashed)
        return real_verify(plain, hashed)

    monkeypatch.setattr(auth_service, "verify_password", recording_verify)

    with pytest.raises(HTTPException):
        auth_service.authenticate_user(UserLogin(email="nobody@example.com", password="whatever"))

    assert len(seen_hashes) == 1
    # The dummy hash must be a valid password hash, otherwise verification raises.
    assert seen_hashes[0] != ""


def test_login_schema_requires_email_only():
    login = UserLogin(email=" Person@Example.COM ", password="secret")
    assert str(login.email) == "person@example.com"

    with pytest.raises(ValidationError):
        UserLogin(password="secret")  # type: ignore[call-arg]

    # The retired username/identifier fallbacks are no longer accepted.
    with pytest.raises(ValidationError):
        UserLogin(username="person", password="secret")  # type: ignore[call-arg]


def test_register_schema_validates_email_and_password_length():
    with pytest.raises(ValidationError):
        UserRegister(email="not-an-email", full_name="Jane Doe", password="supersecret")

    with pytest.raises(ValidationError):
        UserRegister(email="user@example.com", full_name="Jane Doe", password="short")

    with pytest.raises(ValidationError):
        UserRegister(email="user@example.com", full_name="J", password="supersecret")
