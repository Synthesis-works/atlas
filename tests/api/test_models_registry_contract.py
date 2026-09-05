"""
Regression tests for the execution models registry contract (Finding 1).

GET /api/v1/models must return the canonical registry entries (provider, model,
display_name, source, available, status) instead of an error envelope caused by
calling a nonexistent factory method. The frontend resolves the target model
from this contract without importing hardcoded local model names.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from apps.backend.main import app
from apps.backend.adapters.factory import AdapterFactory
from packages.llm.registry import ModelRegistry

client = TestClient(app)

CANONICAL_KEYS = {"provider", "model", "display_name", "source", "available", "status"}


def test_adapter_factory_exposes_registry_models():
    """The factory surfaces registry entries with the canonical keys."""
    models = AdapterFactory.get_available_models()
    assert isinstance(models, list)
    assert len(models) > 0
    for entry in models:
        assert CANONICAL_KEYS.issubset(entry)
        assert isinstance(entry["model"], str)
        assert entry["model"]


def test_models_endpoint_returns_registry_entries():
    """The endpoint wraps registry data in the success envelope, never an error."""
    sample = [
        {
            "provider": "google",
            "model": "gemini-3.5-flash-lite",
            "display_name": "Gemini 3.5 Flash Lite",
            "source": "cloud",
            "available": True,
            "status": "AVAILABLE",
            "capabilities": ["chat"],
        },
        {
            "provider": "ollama",
            "model": "ollama-offline",
            "display_name": "Ollama (Offline)",
            "source": "local",
            "available": False,
            "status": "OFFLINE",
            "capabilities": [],
        },
    ]
    with patch.object(AdapterFactory, "get_available_models", return_value=sample):
        res = client.get("/api/v1/models")
    assert res.status_code == 200
    body = res.json()
    assert body.get("success", True) is True
    assert body["data"] == sample
    for entry in body["data"]:
        assert "model" in entry
        assert "status" in entry


def test_registry_entries_are_honest_about_availability():
    """Registry entries never claim AVAILABLE without the required config."""
    registry_models = ModelRegistry.get_all_models()
    assert registry_models
    for entry in registry_models:
        assert entry["available"] is (entry["status"] == "AVAILABLE")
        assert entry["provider"]
        assert entry["model"]
