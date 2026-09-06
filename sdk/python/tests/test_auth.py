"""Tests for auth DTOs and token supply."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from atlas_sdk.auth import StaticTokenSupplier
from atlas_sdk.models.auth import AuthUserRead, TokenResponse


class TestTokenResponse:
    def test_parse_login_response(self) -> None:
        data = {"access_token": "eyJhbG...", "token_type": "bearer"}
        model = TokenResponse.model_validate(data)
        assert model.access_token == "eyJhbG..."
        assert model.token_type == "bearer"

    def test_default_token_type(self) -> None:
        model = TokenResponse(access_token="tok123")
        assert model.token_type == "bearer"


class TestAuthUserRead:
    def test_parse_full_user(self) -> None:
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": False,
            "org_id": None,
        }
        model = AuthUserRead.model_validate(data)
        assert str(model.id) == "550e8400-e29b-41d4-a716-446655440000"
        assert model.email == "user@example.com"
        assert model.full_name == "Test User"
        assert model.is_active is True
        assert model.is_verified is False
        assert model.org_id is None

    def test_parse_with_org(self) -> None:
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": True,
            "org_id": "660e8400-e29b-41d4-a716-446655440000",
        }
        model = AuthUserRead.model_validate(data)
        assert str(model.org_id) == "660e8400-e29b-41d4-a716-446655440000"

    def test_rejects_missing_required_field(self) -> None:
        data = {"id": "550e8400-e29b-41d4-a716-446655440000"}
        with pytest.raises(ValidationError):
            AuthUserRead.model_validate(data)


class TestStaticTokenSupplier:
    def test_returns_fixed_token(self) -> None:
        supplier = StaticTokenSupplier("fixed-token")
        assert supplier() == "fixed-token"
        assert supplier() == "fixed-token"  # stable across calls
