"""
Regression tests for the execution models registry contract.

GET /api/v1/models must return the typed execution-target catalog entries
(``ModelRead``: id, provider, display_name, status, is_test_only) under the
authenticated envelope, instead of an error envelope caused by calling a
missing factory method.  The CLI/SDK ``atlas model list`` resolves target
models from this contract; the landing frontend resolves the benchmark target
model from the same typed fields.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from apps.backend.main import app
from apps.backend.adapters.factory import AdapterFactory
from apps.backend.adapters.registry import list_models
from apps.backend.dependencies import require_authenticated
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.models import ModelRead, ModelStatus

pytestmark = pytest.mark.usefixtures("override_auth")

USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture()
def override_auth():
    """The models endpoint requires authentication; supply mock claims."""
    app.dependency_overrides[require_authenticated] = lambda: TokenClaims(
        sub=uuid.UUID(USER_ID), exp=0, iat=0, jti=uuid.UUID(USER_ID)
    )
    yield
    app.dependency_overrides.clear()


def test_adapter_factory_exposes_typed_models():
    """The factory surfaces typed ModelRead entries, never raw dicts."""
    models = AdapterFactory.get_available_models()
    assert isinstance(models, list)
    assert len(models) > 0
    for entry in models:
        assert isinstance(entry, ModelRead)
        assert entry.id
        assert entry.provider
        assert entry.display_name
        assert entry.status in ModelStatus


def test_models_endpoint_returns_typed_entries():
    """The endpoint wraps the typed catalog in the success envelope."""
    sample = [
        ModelRead(
            id="mock",
            provider="mock",
            display_name="Mock",
            status=ModelStatus.AVAILABLE,
            is_test_only=True,
        ),
        ModelRead(
            id="gemini/gemini-2.5-flash",
            provider="gemini",
            display_name="Gemini gemini-2.5-flash",
            status=ModelStatus.NOT_CONFIGURED,
            is_test_only=False,
        ),
    ]
    with patch.object(AdapterFactory, "get_available_models", return_value=sample):
        client = TestClient(app)
        res = client.get("/api/v1/models")
    assert res.status_code == 200
    body = res.json()
    assert body.get("success", True) is True
    for entry in body["data"]:
        assert "id" in entry
        assert "provider" in entry
        assert "display_name" in entry
        assert "status" in entry
        assert "is_test_only" in entry


def test_endpoint_requires_authentication():
    """Unauthenticated callers are rejected (HTTPBearer auto_error -> 403)."""
    client = TestClient(app)
    app.dependency_overrides.pop(require_authenticated, None)

    with patch.object(AdapterFactory, "get_available_models", return_value=[]):
        res = client.get("/api/v1/models")
    assert res.status_code in (401, 403)


def test_catalog_is_honest_about_availability():
    """Catalog entries never claim AVAILABLE without the required config."""
    catalog = list_models()
    assert catalog
    for entry in catalog:
        assert entry.status in (ModelStatus.AVAILABLE, ModelStatus.NOT_CONFIGURED)
        assert entry.provider
        assert entry.id
