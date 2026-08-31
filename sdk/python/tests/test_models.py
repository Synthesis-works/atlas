"""Tests for ``AtlasClient.list_models`` and the model catalog DTOs (Slice 7).

Uses ``pytest-httpx`` for mock transport; no live Atlas deployment required.
"""

from __future__ import annotations

import json

import pytest

from atlas_sdk import ModelStatus
from atlas_sdk.auth import StaticTokenSupplier
from atlas_sdk.client import AtlasClient
from atlas_sdk.errors import ValidationError
from atlas_sdk.models.models import ModelRead


def _ok(data: dict | list, *, message: str = "ok") -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


def _entry(
    id: str,
    provider: str,
    *,
    status: str = "AVAILABLE",
    is_test_only: bool = False,
) -> dict:
    return {
        "id": id,
        "provider": provider,
        "display_name": id.split("/")[-1],
        "status": status,
        "is_test_only": is_test_only,
    }


_URL = "http://localhost:8000/api/v1/models"


class TestListModels:
    def test_list_models_returns_dtos(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_URL,
            json=_ok(
                [
                    _entry("mock", "mock", is_test_only=True),
                    _entry("groq/llama-3.1-8b-instant", "groq", status="NOT_CONFIGURED"),
                ]
            ),
        )
        client = AtlasClient("http://localhost:8000")
        models = client.list_models()
        assert len(models) == 2
        assert isinstance(models[0], ModelRead)
        assert models[0].id == "mock"
        assert models[0].provider == "mock"
        assert models[0].status is ModelStatus.AVAILABLE
        assert models[0].is_test_only is True
        assert models[1].id == "groq/llama-3.1-8b-instant"
        assert models[1].status is ModelStatus.NOT_CONFIGURED
        assert models[1].is_test_only is False
        client.close()

    def test_list_models_hits_models_path(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(method="GET", url=_URL, json=_ok([_entry("mock", "mock")]))
        client = AtlasClient("http://localhost:8000")
        client.list_models()
        request = httpx_mock.get_request()
        assert request is not None
        assert request.url.path == "/api/v1/models"
        client.close()

    def test_list_models_sends_auth_header(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(method="GET", url=_URL, json=_ok([_entry("mock", "mock")]))
        client = AtlasClient(
            "http://localhost:8000", token_supplier=StaticTokenSupplier("my-tok")
        )
        client.list_models()
        request = httpx_mock.get_request()
        assert request is not None
        assert request.headers.get("authorization") == "Bearer my-tok"
        client.close()

    def test_list_models_invalid_status_raises_validation_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_URL,
            json=_ok([_entry("mock", "mock", status="WEIRD")]),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError):
            client.list_models()
        client.close()

    def test_list_models_missing_fields_raises_validation_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_URL,
            json=_ok([{"id": "mock", "status": "AVAILABLE"}]),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError):
            client.list_models()
        client.close()


class TestModelStatus:
    def test_status_values(self) -> None:
        assert ModelStatus.AVAILABLE.value == "AVAILABLE"
        assert ModelStatus.NOT_CONFIGURED.value == "NOT_CONFIGURED"

    def test_serializes_to_plain_string(self) -> None:
        model = ModelRead(
            id="mock",
            provider="mock",
            display_name="Mock",
            status=ModelStatus.NOT_CONFIGURED,
            is_test_only=True,
        )
        dumped = json.loads(model.model_dump_json())
        assert dumped["status"] == "NOT_CONFIGURED"
