"""Tests for API response envelope DTOs."""

from __future__ import annotations

from atlas_sdk.models.responses import APIErrorResponse, APIResponse, ErrorDetail


class TestAPIResponse:
    def test_parse_success(self) -> None:
        data = {
            "success": True,
            "message": "ok",
            "data": {"status": "healthy", "version": "0.9.0"},
            "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
        }
        model = APIResponse[dict].model_validate(data)
        assert model.success is True
        assert model.data["status"] == "healthy"
        assert model.meta.request_id == "req-1"


class TestAPIErrorResponse:
    def test_parse_error(self) -> None:
        data = {
            "success": False,
            "error": {"code": "UNAUTHORIZED", "message": "token expired", "details": None},
            "meta": {"request_id": "req-2", "timestamp": "2026-01-01T00:00:00Z"},
        }
        model = APIErrorResponse.model_validate(data)
        assert model.success is False
        assert model.error.code == "UNAUTHORIZED"
        assert model.error.message == "token expired"


class TestErrorDetail:
    def test_with_details(self) -> None:
        data = {"code": "VALIDATION", "message": "bad input", "details": {"field": "email"}}
        model = ErrorDetail.model_validate(data)
        assert model.details == {"field": "email"}

    def test_without_details(self) -> None:
        data = {"code": "X", "message": "y"}
        model = ErrorDetail.model_validate(data)
        assert model.details is None
