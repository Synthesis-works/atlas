"""Tests for the CLI agent tool layer (Phase 2).

The tool layer exposes Atlas capabilities through the existing ``AtlasClient``
(never raw HTTP/shell).  Each tool validates its arguments, delegates to an
``AtlasClient`` method, and returns a compact, bounded observation.  Tools are
classified READ vs WRITE so Phase 4's REPL can gate mutating operations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from atlas_sdk.models.benchmarks import BenchmarkRead, BenchmarkVersionRead, PageResponse
from atlas_sdk.models.executions import ExecutionResponse
from atlas_sdk.models.leaderboard import LeaderboardEntryRead, LeaderboardRead, ModelSummary
from atlas_sdk.models.models import ModelRead, ModelStatus
from atlas_sdk.models.reports import ReportSummaryRead

from cli.agent.tools.base import AgentPermission, BaseTool, ToolResult
from cli.agent.tools.registry import ToolRegistry

# ────────────────────────────────────────────────────────────────────────────


def _id(n: int = 1) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-0000-0000-00000000000{n}")


def _mock_client() -> MagicMock:
    mock = MagicMock()
    mock.list_benchmarks.return_value = PageResponse(
        items=[BenchmarkRead(id=_id(1), project_id=_id(9), state="published", name="B1")],
        total=1,
        limit=50,
    )
    mock.list_benchmark_versions.return_value = [
        BenchmarkVersionRead(
            id=_id(2),
            benchmark_id=_id(1),
            version_string="1.0.0",
            state="published",
        )
    ]
    mock.list_models.return_value = [
        ModelRead(id="mock", provider="test", display_name="Mock", status=ModelStatus.AVAILABLE)
    ]
    mock.get_execution.return_value = ExecutionResponse(
        id=_id(3),
        benchmark_version_id=_id(2),
        status="COMPLETED",
        target_model="mock",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        created_by=_id(9),
    )
    mock.submit_execution.return_value = ExecutionResponse(
        id=_id(4),
        benchmark_version_id=_id(2),
        status="QUEUED",
        target_model="mock",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        created_by=_id(9),
    )
    mock.get_report_run.return_value = ReportSummaryRead(
        run_id=_id(5),
        benchmark_id=_id(1),
        benchmark_name="B1",
        benchmark_version="1.0.0",
        target_model="mock",
        evaluation_status="COMPLETED",
        overall_score=92.5,
    )
    mock.get_benchmark_leaderboard.return_value = LeaderboardRead(
        leaderboard_type="BENCHMARK",
        title="Mock Board",
        benchmark_version_id=str(_id(2)),
        entries=PageResponse(
            items=[
                LeaderboardEntryRead(
                    rank=1,
                    model_name="mock",
                    overall_score=92.5,
                    benchmark_count=3,
                    last_updated=datetime(2026, 1, 1, tzinfo=UTC),
                )
            ],
            total=1,
            limit=20,
            offset=0,
        ),
    )
    mock.get_model_summary.return_value = ModelSummary(
        model="mock", benchmarks=3, average_score=90.0
    )
    return mock


class TestToolResult:
    def test_success(self) -> None:
        r = ToolResult(summary="ok", data={"a": 1})
        assert r.ok is True
        assert r.summary == "ok"
        assert r.data == {"a": 1}

    def test_failure(self) -> None:
        r = ToolResult(ok=False, summary="failed", error="boom")
        assert r.ok is False
        assert r.error == "boom"


class TestBaseTool:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            BaseTool()  # type: ignore[abstract]

    def test_gemini_schema_shape(self) -> None:
        from cli.agent.tools.library import ListBenchmarksTool

        decl = ListBenchmarksTool().get_gemini_schema()
        assert decl["name"] == "list_benchmarks"
        assert "description" in decl
        assert decl["parameters"]["type"] == "OBJECT"
        assert isinstance(decl["parameters"]["properties"], dict)


class TestToolRegistry:
    def test_all_tools_registered(self) -> None:
        reg = ToolRegistry()
        names = set(reg.registry.keys())
        for expected in {
            "list_benchmarks",
            "get_benchmark_versions",
            "list_models",
            "submit_run",
            "get_run",
            "watch_run",
            "get_report",
            "export_report",
            "get_leaderboard",
            "get_model_summary",
            "get_activity",
            "get_dashboard",
            "get_health",
            "whoami",
        }:
            assert expected in names

    def test_gemini_declarations_are_unique_and_valid(self) -> None:
        reg = ToolRegistry()
        decls = reg.get_gemini_declarations()
        names = [d["name"] for d in decls]
        assert len(names) == len(set(names))
        for d in decls:
            assert "name" in d
            assert "description" in d
            assert d["parameters"]["type"] == "OBJECT"

    def test_execute_unknown_tool_raises(self) -> None:
        reg = ToolRegistry()
        with pytest.raises(ValueError):
            reg.execute("no_such_tool", _mock_client(), {})

    def test_is_mutating(self) -> None:
        reg = ToolRegistry()
        assert reg.is_mutating("submit_run") is True
        assert reg.is_mutating("export_report") is True
        assert reg.is_mutating("list_benchmarks") is False
        assert reg.is_mutating("get_run") is False

    def test_permission_values(self) -> None:
        assert AgentPermission.READ.value == "READ"
        assert AgentPermission.WRITE.value == "WRITE"

    def test_execute_delegates_to_client(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("list_benchmarks", client, {"limit": 5})
        assert result.ok is True
        client.list_benchmarks.assert_called_once_with(limit=5)


class TestListBenchmarks:
    def test_delegates_with_default_and_result(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("list_benchmarks", client, {})
        client.list_benchmarks.assert_called_once_with(limit=50)
        assert result.ok is True
        assert "B1" in result.summary

    def test_rejects_non_int_limit(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("list_benchmarks", _mock_client(), {"limit": "x"})
        assert result.ok is False
        assert result.error


class TestGetBenchmarkVersions:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("get_benchmark_versions", client, {"benchmark_id": str(_id(1))})
        client.list_benchmark_versions.assert_called_once_with(str(_id(1)))
        assert result.ok is True
        assert "1.0.0" in result.summary

    def test_missing_benchmark_id_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("get_benchmark_versions", _mock_client(), {})
        assert result.ok is False


class TestListModels:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("list_models", client, {})
        client.list_models.assert_called_once_with()
        assert result.ok is True
        assert "mock" in result.summary


class TestSubmitRun:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "submit_run",
            client,
            {"benchmark_version_id": str(_id(2)), "target_model": "mock"},
        )
        client.submit_execution.assert_called_once_with(
            str(_id(2)), target_model="mock", dataset_version_id=None
        )
        assert result.ok is True
        assert "QUEUED" in result.summary

    def test_missing_required_args_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("submit_run", _mock_client(), {})
        assert result.ok is False


class TestGetRun:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("get_run", client, {"execution_id": str(_id(3))})
        client.get_execution.assert_called_once_with(str(_id(3)))
        assert result.ok is True
        assert "COMPLETED" in result.summary


class TestWatchRun:
    @pytest.fixture(autouse=True)
    def _no_sleep(self) -> None:
        with patch("cli.agent.tools.library.time.sleep"):
            yield

    def test_polls_until_terminal(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("watch_run", client, {"execution_id": str(_id(3)), "max_polls": 1})
        assert result.ok is True
        assert "COMPLETED" in result.summary

    def test_bounded_polls(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        client.get_execution.side_effect = None
        client.get_execution.return_value = ExecutionResponse(
            id=_id(3),
            benchmark_version_id=_id(2),
            status="RUNNING",
            target_model="mock",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            created_by=_id(9),
        )
        result = reg.execute("watch_run", client, {"execution_id": str(_id(3)), "max_polls": 3})
        assert client.get_execution.call_count <= 3
        assert result.ok is True
        assert "RUNNING" in result.summary


class TestGetReport:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("get_report", client, {"run_id": str(_id(5))})
        client.get_report_run.assert_called_once_with(str(_id(5)))
        assert result.ok is True
        assert "92.5" in result.summary


class TestExportReport:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        client.export_report_run.return_value = MagicMock(content=b"data", filename="r.json")
        result = reg.execute("export_report", client, {"run_id": str(_id(5)), "format": "json"})
        client.export_report_run.assert_called_once_with(
            str(_id(5)), format_type="json", include_prompt=False, include_expected_output=False
        )
        assert result.ok is True
        assert "r.json" in result.summary

    def test_is_flagged_mutating(self) -> None:
        reg = ToolRegistry()
        assert reg.is_mutating("export_report") is True


class TestLeaderboard:
    def test_get_leaderboard_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("get_leaderboard", client, {"benchmark_version_id": str(_id(2))})
        client.get_benchmark_leaderboard.assert_called_once_with(str(_id(2)), limit=20, offset=0)
        assert result.ok is True
        assert "mock" in result.summary

    def test_model_summary_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("get_model_summary", client, {"model_name": "mock"})
        client.get_model_summary.assert_called_once_with("mock")
        assert result.ok is True
        assert "90" in result.summary
