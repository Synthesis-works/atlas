"""Shared test fixtures for atlas-sdk tests."""

from __future__ import annotations

import httpx
import pytest

from atlas_sdk.auth import StaticTokenSupplier
from atlas_sdk.client import AtlasClient


@pytest.fixture()
def token() -> str:
    return "eyJhbGciOiJIUzI1NiJ9.test-token-payload"


@pytest.fixture()
def supplier(token: str) -> StaticTokenSupplier:
    return StaticTokenSupplier(token)


@pytest.fixture()
def base_url() -> str:
    return "http://localhost:8000"


@pytest.fixture()
def client(base_url: str, supplier: StaticTokenSupplier) -> AtlasClient:
    return AtlasClient(base_url, token_supplier=supplier)


def _make_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Build a fake ``httpx.Response`` without network I/O."""
    content = b""
    if json_data is not None:
        import json as _json

        content = _json.dumps(json_data).encode()
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=headers or {},
        request=httpx.Request("GET", "http://test.invalid"),
    )
