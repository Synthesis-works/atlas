"""Tests for the execution-target model catalog (Slice 7).

Covers ``apps.backend.adapters.registry.list_models`` and the mounted
``GET /api/v1/models`` endpoint.  Invariants:
  - ``mock`` is always present, test-only, and AVAILABLE;
  - every catalog ``id`` parses in ``resolve_provider_and_model`` to its own
    provider (enumerator and resolver agree by construction);
  - a provider's models are ``NOT_CONFIGURED`` exactly when ``health()``
    fails — the same gate the execution path applies;
  - the deployment's ``config/providers.json`` models and the app-code
    defaults are surfaced.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.adapters.registry import (
    DEFAULT_TARGET_MODELS,
    list_models,
)
from apps.backend.dependencies import require_authenticated
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.models import ModelRead, ModelStatus
from packages.llm.clients.adapter import ProviderAdapter


class _StubClient:
    """A minimal BaseLLMClient stand-in with deterministic health/models."""

    def __init__(self, *, healthy: bool, models: list[str] | None = None) -> None:
        self._healthy = healthy
        self._models = models or []

    def health(self) -> bool:
        return self._healthy

    def list_models(self) -> list[str]:
        return list(self._models)


def _stub_adapter(**providers: _StubClient) -> ProviderAdapter:
    """A real ProviderAdapter with selected clients stubbed out.

    The resolver still runs on the real instance; only availability and
    model claims are stubbed, keeping statuses deterministic.
    """
    adapter = ProviderAdapter()
    for provider, stub in providers.items():
        adapter.clients[provider] = stub
    return adapter


def _catalog(**providers: _StubClient) -> list[ModelRead]:
    return list_models(adapter=_stub_adapter(**providers))


def _all_real_providers(*, healthy: bool) -> dict[str, _StubClient]:
    return {
        provider: _StubClient(healthy=healthy, models=[f"{provider}-model"])
        for provider in ("ollama", "gemini", "grok", "mistral", "groq", "nvidia")
    }


# ── mock is always present ────────────────────────────────────────────────


def test_mock_always_present_and_test_only() -> None:
    catalog = _catalog(**_all_real_providers(healthy=False))
    mock_entries = [m for m in catalog if m.provider == "mock"]
    assert len(mock_entries) == 1
    entry = mock_entries[0]
    assert entry.id == "mock"
    assert entry.status is ModelStatus.AVAILABLE
    assert entry.is_test_only is True


# ── enumerator and resolver agree ─────────────────────────────────────────


def test_every_id_resolves_to_its_own_provider() -> None:
    resolver = ProviderAdapter()
    catalog = _catalog(**_all_real_providers(healthy=False))
    assert len(catalog) >= 2
    for entry in catalog:
        provider, model = resolver.resolve_provider_and_model(entry.id)
        assert provider == entry.provider
        if entry.provider != "mock":
            assert model == entry.id.split("/", 1)[1]


# ── status mirrors health() ───────────────────────────────────────────────


def test_catalog_normalizes_prefixed_client_models() -> None:
    """Client static lists that already carry ``provider/`` must collapse to one
    canonical id — ``groq/groq/x`` is invalid (the resolver would mis-parse it)."""
    providers = _all_real_providers(healthy=True)
    providers["groq"] = _StubClient(
        healthy=True,
        models=["groq/llama-3.1-8b-instant", "llama-3.1-8b-instant"],
    )
    providers["nvidia"] = _StubClient(
        healthy=True,
        models=["nvidia/neva-22b", "meta/llama-3.1-8b-instruct"],
    )
    catalog = _catalog(**providers)
    ids = [m.id for m in catalog]
    assert "groq/llama-3.1-8b-instant" in ids
    assert "groq/groq/llama-3.1-8b-instant" not in ids
    assert "nvidia/neva-22b" in ids
    assert "nvidia/nvidia/neva-22b" not in ids
    assert "nvidia/meta/llama-3.1-8b-instruct" in ids
    assert ids.count("groq/llama-3.1-8b-instant") == 1


def test_status_available_when_providers_healthy() -> None:
    catalog = _catalog(**_all_real_providers(healthy=True))
    real_entries = [m for m in catalog if m.provider != "mock"]
    assert real_entries
    assert all(m.status is ModelStatus.AVAILABLE for m in real_entries)


def test_status_not_configured_when_providers_unhealthy() -> None:
    catalog = _catalog(**_all_real_providers(healthy=False))
    real_entries = [m for m in catalog if m.provider != "mock"]
    assert real_entries
    assert all(m.status is ModelStatus.NOT_CONFIGURED for m in real_entries)


def test_status_is_per_provider() -> None:
    providers = _all_real_providers(healthy=True)
    providers["ollama"] = _StubClient(healthy=True, models=["qwen"])
    providers["gemini"] = _StubClient(healthy=False, models=["gemini-2.5-flash"])
    catalog = _catalog(**providers)
    by_provider = {m.provider: m.status for m in catalog}
    assert by_provider["ollama"] is ModelStatus.AVAILABLE
    assert by_provider["gemini"] is ModelStatus.NOT_CONFIGURED


# ── configured provider models and app defaults ───────────────────────────


def test_catalog_surfaces_configured_provider_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "apps.backend.adapters.registry._provider_config_models",
        lambda: {"gemini": "gemini-custom-1", "ollama": "qwen-custom"},
    )
    catalog = _catalog(
        **{
            "ollama": _StubClient(healthy=True),
            "gemini": _StubClient(healthy=True),
            **_all_real_providers(healthy=True),
        }
    )
    ids = {m.id for m in catalog}
    assert "gemini/gemini-custom-1" in ids
    assert "ollama/qwen-custom" in ids


def test_catalog_surfaces_app_defaults() -> None:
    resolver = ProviderAdapter()
    catalog = _catalog(
        **{
            "ollama": _StubClient(healthy=True),
            "gemini": _StubClient(healthy=True),
            "groq": _StubClient(healthy=True),
            **_all_real_providers(healthy=True),
        }
    )
    ids = {m.id for m in catalog}
    for default in DEFAULT_TARGET_MODELS:
        provider, model = resolver.resolve_provider_and_model(default)
        canonical = "mock" if provider == "mock" else f"{provider}/{model}"
        assert canonical in ids


# ── adapter factory delegation ────────────────────────────────────────────


def test_adapter_factory_delegates_to_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = [
        ModelRead(
            id="groq/llama-3.1-8b-instant",
            provider="groq",
            display_name="Groq llama-3.1-8b-instant",
            status=ModelStatus.NOT_CONFIGURED,
            is_test_only=False,
        )
    ]
    monkeypatch.setattr("apps.backend.adapters.factory.list_models", lambda: expected)
    assert AdapterFactory.get_available_models() == expected


# ── router ────────────────────────────────────────────────────────────────


@pytest.fixture
def authed_client(monkeypatch: pytest.MonkeyPatch):
    def override_claims() -> TokenClaims:
        return TokenClaims(
            sub=uuid.uuid4(),
            exp=9999999999,
            iat=1000000000,
            jti=uuid.uuid4(),
        )

    app.dependency_overrides[require_authenticated] = override_claims
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_router_requires_authentication() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/models")
    assert response.status_code == 401
    client.close()


def test_router_returns_model_envelope(
    authed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    models = [
        ModelRead(
            id="mock",
            provider="mock",
            display_name="Mock",
            status=ModelStatus.AVAILABLE,
            is_test_only=True,
        ),
        ModelRead(
            id="groq/llama-3.1-8b-instant",
            provider="groq",
            display_name="Groq llama-3.1-8b-instant",
            status=ModelStatus.NOT_CONFIGURED,
            is_test_only=False,
        ),
    ]
    monkeypatch.setattr(
        "apps.backend.adapters.factory.AdapterFactory.get_available_models",
        lambda: models,
    )
    response = authed_client.get("/api/v1/models")
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["success"] is True
    data = body["data"]
    assert len(data) == 2
    assert data[0]["id"] == "mock"
    assert data[0]["status"] == "AVAILABLE"
    assert data[0]["is_test_only"] is True
    assert data[1]["status"] == "NOT_CONFIGURED"
