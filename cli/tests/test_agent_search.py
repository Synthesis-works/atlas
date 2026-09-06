"""Tests for the CLI search agent tool (v3.5 project-scoped retrieval).

Covers registration, READ classification (never confirms), and delegation to
the SDK ``search`` method.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from atlas_sdk.models.benchmarks import PageResponse
from atlas_sdk.models.search import SearchResult

from cli.agent.tools.registry import ToolRegistry

PROJECT = str(uuid.uuid4())


def _result(i: int, entity: str = "benchmark", title: str = "Benchmark") -> SearchResult:
    return SearchResult(
        id=uuid.uuid4(),
        entity_type=entity,
        title=f"{title} {i}",
        subtitle="Status: PUBLISHED",
        description=None,
        url=f"/{entity}s/{i}",
        score=0.9 - i * 0.1,
        metadata={"project_id": PROJECT, "status": "PUBLISHED"},
    )


def _mock_client(items: list[SearchResult] | None = None) -> MagicMock:
    mock = MagicMock()
    mock_items = items or [_result(1), _result(2, "execution", "Execution")]
    mock.search.return_value = PageResponse(
        items=mock_items,
        total=len(mock_items),
        limit=20,
        offset=0,
    )
    return mock


class TestSearchRegistered:
    def test_search_tool_present(self) -> None:
        reg = ToolRegistry()
        assert "search" in reg.registry

    def test_search_is_read(self) -> None:
        reg = ToolRegistry()
        assert reg.is_mutating("search") is False
        assert reg.is_destructive("search") is False


class TestSearchTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("search", client, {"project_id": PROJECT, "q": "counting", "limit": 5})
        client.search.assert_called_once_with(PROJECT, "counting", entity_types=None, limit=5)
        assert result.ok is True
        assert "counting" in result.summary
        assert result.data["total"] == 2

    def test_scopes_to_entity_type(self) -> None:
        reg = ToolRegistry()
        client = _mock_client([_result(1)])
        result = reg.execute(
            "search",
            client,
            {"project_id": PROJECT, "q": "run", "entity_types": ["execution"]},
        )
        client.search.assert_called_once_with(PROJECT, "run", entity_types=["execution"], limit=20)
        assert result.ok is True
        assert result.data["items"][0]["entity_type"] == "benchmark"

    def test_returns_summary(self) -> None:
        reg = ToolRegistry()
        client = _mock_client([_result(1)])
        result = reg.execute("search", client, {"project_id": PROJECT, "q": "count"})
        assert result.ok is True
        assert "[benchmark]" in result.summary
        assert str(result.data["items"][0]["id"]) in result.summary

    def test_missing_query_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("search", _mock_client(), {"project_id": PROJECT})
        assert result.ok is False
        assert result.error
