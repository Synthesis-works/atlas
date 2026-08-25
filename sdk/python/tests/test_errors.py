"""Tests for error hierarchy."""

from __future__ import annotations

import pytest

from atlas_sdk.errors import (
    ApiError,
    AuthError,
    ConflictError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    RateLimitedError,
    ServerError,
    ValidationError,
    error_for_status,
)


class TestErrorHierarchy:
    def test_auth_error(self) -> None:
        err = AuthError(status=401, message="unauthorized")
        assert err.status == 401
        assert err.message == "unauthorized"
        assert isinstance(err, ApiError)

    def test_forbidden_error(self) -> None:
        err = ForbiddenError(status=403)
        assert isinstance(err, ApiError)

    def test_not_found_error(self) -> None:
        err = NotFoundError(status=404)
        assert isinstance(err, ApiError)

    def test_validation_error(self) -> None:
        err = ValidationError(status=422, details={"field": "email"})
        assert err.details == {"field": "email"}

    def test_conflict_error(self) -> None:
        err = ConflictError(status=409)
        assert isinstance(err, ApiError)

    def test_rate_limited_error(self) -> None:
        err = RateLimitedError(status=429)
        assert isinstance(err, ApiError)

    def test_server_error(self) -> None:
        err = ServerError(status=500)
        assert isinstance(err, ApiError)

    def test_network_error(self) -> None:
        err = NetworkError(message="connection refused")
        assert "connection refused" in str(err)
        assert not isinstance(err, ApiError)

    def test_str_repr_uses_message(self) -> None:
        err = ApiError(status=418, message="teapot")
        assert str(err) == "teapot"

    def test_str_repr_falls_back_to_code(self) -> None:
        err = ApiError(status=418, code="I_M_A_TEAPOT")
        assert str(err) == "I_M_A_TEAPOT"

    def test_str_repr_falls_back_to_status(self) -> None:
        err = ApiError(status=418)
        assert str(err) == "HTTP 418"


class TestErrorForStatus:
    @pytest.mark.parametrize(
        "status,expected",
        [
            (401, AuthError),
            (403, ForbiddenError),
            (404, NotFoundError),
            (409, ConflictError),
            (422, ValidationError),
            (429, RateLimitedError),
            (500, ServerError),
            (502, ServerError),
            (503, ServerError),
            (504, ServerError),
        ],
    )
    def test_maps_correctly(self, status: int, expected: type[ApiError]) -> None:
        err = error_for_status(status, message="test")
        assert isinstance(err, expected)
        assert err.status == status

    def test_unknown_4xx_falls_back_to_base(self) -> None:
        err = error_for_status(418)
        assert type(err) is ApiError
        assert err.status == 418
