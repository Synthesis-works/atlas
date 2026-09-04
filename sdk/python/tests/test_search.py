"""Tests for AtlasClient.search (v3.5 project-scoped retrieval).

Uses ``pytest-httpx`` for mock transport; no live Atlas deployment required.
The search endpoint returns ``PageResponse[SearchResult]`` directly (not
wrapped in ``APIResponse``), mirroring the execution endpoints.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from atlas_sdk.client import AtlasClient
from atlas_sdk.errors import (
    AuthError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    ServerError,
)
from atlas_sdk.models.benchmarks import PageResponse
from atlas_sdk.models.search import SearchResult


def _err(status: int, code: str = "", message: str = "") -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


PROJECT = "732bb328-d628-4041-8dad-641436b05afa"


def _url(**params) -> str:
    base = f"http://localhost:8000/api/v1/projects/{PROJECT}/search"
    if params:
        from urllib.parse import urlencode

        base += "?" + urlencode(params)
    return base


def _page_payload(**overrides) -> dict:
    payload = {
        "items": [
            {
                "id": str(uuid.uuid4()),
                "entity_type": "benchmark",
                "title": "Counting benchmark",
                "subtitle": "Status: PUBLISHED",
                "description": "Counts things",
                "url": "/benchmarks/1",
                "score": 0.9,
                "metadata": {"project_id": PROJECT, "status": "PUBLISHED"},
            },
            {
                "id": str(uuid.uuid4()),
                "entity_type": "execution",
                "title": "Execution for mock",
                "subtitle": "Status: COMPLETED",
                "description": None,
                "url": "/executions/2",
                "score": 0.8,
                "metadata": {"project_id": PROJECT, "status": "COMPLETED"},
            },
        ],
        "total": 2,
        "limit": 20,
        "offset": 0,
        "next_cursor": None,
    }
    payload.update(overrides)
    return payload


class TestSearchDtos:
    def test_search_result_parse(self) -> None:
        data = _page_payload()["items"][0]
        result = SearchResult.model_validate(data)
        assert result.entity_type == "benchmark"
        assert result.score == 0.9
        assert result.metadata["project_id"] == PROJECT

    def test_page_parse(self) -> None:
        page = PageResponse[SearchResult].model_validate(_page_payload())
        assert page.total == 2
        assert page.limit == 20
        assert isinstance(page.items[0], SearchResult)


class TestSearch:
    def test_success(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(q="counting", limit="20"),
            json=_page_payload(),
        )
        client = AtlasClient("http://localhost:8000")
        page = client.search(PROJECT, "counting")
        assert isinstance(page, PageResponse)
        assert page.total == 2
        assert page.items[0].entity_type == "benchmark"
        client.close()

    def test_entity_types_param(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(q="counting", limit="20", entity_types="benchmark,execution"),
            json=_page_payload(),
        )
        client = AtlasClient("http://localhost:8000")
        client.search(PROJECT, "counting", entity_types=["benchmark", "execution"])
        client.close()

    def test_custom_limit(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(method="GET", url=_url(q="x", limit="5"), json=_page_payload())
        client = AtlasClient("http://localhost:8000")
        client.search(PROJECT, "x", limit=5)
        client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(q="x", limit="20"),
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError):
            client.search(PROJECT, "x")
        client.close()

    def test_403_raises_forbidden(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(q="x", limit="20"),
            status_code=403,
            json=_err(403, "FORBIDDEN", "Not a member"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError):
            client.search(PROJECT, "x")
        client.close()

    def test_404_raises_not_found(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(q="x", limit="20"),
            status_code=404,
            json=_err(404, "NOT_FOUND", "Project not found"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError):
            client.search(PROJECT, "x")
        client.close()

    def test_500_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(q="x", limit="20"),
            status_code=500,
            json=_err(500, "INTERNAL", "boom"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.search(PROJECT, "x")
        client.close()

    def test_connect_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.search(PROJECT, "x")
        client.close()


