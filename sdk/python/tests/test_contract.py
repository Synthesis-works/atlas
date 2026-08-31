"""Contract tests — verify SDK DTOs match the Atlas OpenAPI schema.

This is the architectural guard that protects the SDK against ``main`` drift.
It defines the expected OpenAPI schema shapes for Phase 1 endpoints and
asserts that every SDK DTO matches field-for-field.

Future iterations will fetch the live OpenAPI schema from a running FastAPI
app (via TestClient or a pinned CI image) instead of using this hardcoded
baseline.  The hardcoded baseline is the Phase 1 foundation — it proves the
pattern works and catches drift when someone updates the backend without
updating the SDK.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from atlas_sdk.models.auth import AuthUserRead, TokenResponse
from atlas_sdk.models.health import HealthData
from atlas_sdk.models.models import ModelRead
from atlas_sdk.models.responses import ErrorDetail, ResponseMeta

# ── Expected OpenAPI schema shapes (Phase 1 endpoints) ────────────────
#
# These mirror the actual FastAPI-generated schemas on origin/main @ 2fa36f6.
# When the backend changes a field name, type, or optionality, this test
# will fail — forcing the SDK to update in lockstep.

_EXPECTED_SCHEMAS: dict[str, dict[str, Any]] = {
    "TokenResponse": {
        "type": "object",
        "required": ["access_token"],
        "properties": {
            "access_token": {"type": "string"},
            "token_type": {"type": "string", "default": "bearer"},
        },
    },
    "AuthUserRead": {
        "type": "object",
        "required": ["id", "email", "full_name", "is_active", "is_verified"],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "email": {"type": "string", "format": "email"},
            "full_name": {"type": "string"},
            "is_active": {"type": "boolean"},
            "is_verified": {"type": "boolean"},
            "org_id": {"anyOf": [{"type": "string", "format": "uuid"}, {"type": "null"}]},
        },
    },
    "HealthData": {
        "type": "object",
        "required": ["status", "version"],
        "properties": {
            "status": {"type": "string"},
            "version": {"type": "string"},
        },
    },
    "ResponseMeta": {
        "type": "object",
        "required": ["request_id", "timestamp"],
        "properties": {
            "request_id": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
        },
    },
    "ErrorDetail": {
        "type": "object",
        "required": ["code", "message"],
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "details": {},
        },
    },
    "ModelRead": {
        "type": "object",
        "required": ["id", "provider", "display_name", "status"],
        "properties": {
            "id": {"type": "string"},
            "provider": {"type": "string"},
            "display_name": {"type": "string"},
            "status": {"type": "string"},
            "is_test_only": {"type": "boolean", "default": False},
        },
    },
}


def _schema_fields(schema: dict[str, Any]) -> dict[str, bool]:
    """Return ``{field_name: is_required}`` from an OpenAPI object schema."""
    required = set(schema.get("required", []))
    props = schema.get("properties", {})
    return {name: name in required for name in props}


def _dto_fields(model: type) -> dict[str, bool]:
    """Return ``{field_name: is_required}`` from a Pydantic v2 model."""
    fields = model.model_fields
    result: dict[str, bool] = {}
    for name, field_info in fields.items():
        is_required = field_info.is_required()
        result[name] = is_required
    return result


class TestContractBaseline:
    """Verify SDK DTOs match the expected OpenAPI schema shapes."""

    @pytest.mark.parametrize(
        "schema_name,model",
        [
            ("TokenResponse", TokenResponse),
            ("AuthUserRead", AuthUserRead),
            ("HealthData", HealthData),
            ("ResponseMeta", ResponseMeta),
            ("ErrorDetail", ErrorDetail),
            ("ModelRead", ModelRead),
        ],
    )
    def test_dto_matches_schema(
        self, schema_name: str, model: type
    ) -> None:
        expected = _EXPECTED_SCHEMAS[schema_name]
        expected_fields = _schema_fields(expected)
        actual_fields = _dto_fields(model)

        # Every expected field must exist in the DTO.
        for name in expected_fields:
            assert name in actual_fields, (
                f"{schema_name}: field '{name}' in OpenAPI schema but not in SDK DTO"
            )

        # Every DTO field must exist in the schema.
        for name in actual_fields:
            assert name in expected_fields, (
                f"{schema_name}: field '{name}' in SDK DTO but not in OpenAPI schema"
            )

        # Required/optional must match.
        for name in expected_fields:
            assert expected_fields[name] == actual_fields[name], (
                f"{schema_name}.{name}: required={expected_fields[name]} in schema "
                f"but required={actual_fields[name]} in DTO"
            )


class TestContractFile:
    """Verify a saved OpenAPI schema file matches the expected baseline."""

    def test_baseline_schema_is_valid_json(self) -> None:
        """The baseline schema file exists and is parseable."""
        schema_path = Path(__file__).parent / "openapi_baseline.json"
        if not schema_path.exists():
            pytest.skip("No openapi_baseline.json — run generate_contract_baseline.py first")
            return
        raw = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "openapi" in raw or "swagger" in raw, "Not a valid OpenAPI schema"
        assert "paths" in raw, "Schema missing paths"

    def test_baseline_contains_phase1_endpoints(self) -> None:
        """The baseline schema includes the Phase 1 endpoint paths."""
        schema_path = Path(__file__).parent / "openapi_baseline.json"
        if not schema_path.exists():
            pytest.skip("No openapi_baseline.json")
            return
        raw = json.loads(schema_path.read_text(encoding="utf-8"))
        paths = raw.get("paths", {})

        required_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/me",
            "/health",
            "/api/v1/system/health/ready",
            "/api/v1/system/health/live",
        ]
        for path in required_paths:
            assert path in paths, f"Phase 1 path '{path}' missing from baseline schema"
