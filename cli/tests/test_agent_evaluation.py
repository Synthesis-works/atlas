"""Tests for the CLI evaluation-parity agent tools (v3.4).

Covers registration, the READ tools, the WRITE tools, and the registry's
write classification (single-confirm, non-destructive).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from atlas_sdk.models.evaluation import (
    EvaluationEnqueuedRead,
    EvaluationResultsRead,
    ExecutionCompareItemRead,
    ExecutionCompareResponse,
    ReportListRead,
    ReportRead,
)

from cli.agent.repl import AgentREPL
from cli.agent.tools.registry import ToolRegistry


def _uuid(n: int) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-0000-0000-0000000000{n:02d}")


PROJECT = str(_uuid(10))
DATASET = str(_uuid(11))
EXEC1 = str(_uuid(12))
EXEC2 = str(_uuid(13))


def _mock_client() -> MagicMock:
    mock = MagicMock()
    mock.enqueue_evaluation.return_value = EvaluationEnqueuedRead(execution_id=_uuid(12))
    mock.get_evaluation_results.return_value = EvaluationResultsRead(
        execution_id=_uuid(12),
        status="completed",
        overall_score=0.85,
        profile_id=_uuid(14),
        total_outputs=3,
        evaluated_outputs=3,
        passed_outputs=2,
        results=[],
    )
    mock.create_evaluation_cases.return_value = MagicMock(
        dataset_id=_uuid(11), written=[], skipped=0
    )
    mock.compare_executions.return_value = ExecutionCompareResponse(
        leaderboard=[
            ExecutionCompareItemRead(
                execution_id=_uuid(12),
                target_model="gemini",
                overall_score=0.9,
                passed_outputs=9,
                total_outputs=10,
                evaluated_outputs=10,
                rank=1,
            )
        ]
    )
    mock.generate_report.return_value = ReportRead(
        id=_uuid(15),
        project_id=_uuid(10),
        name="Q1 Report",
        created_at="2026-09-01T12:00:00Z",
        updated_at="2026-09-01T12:00:00Z",
        versions=[],
    )
    mock.list_reports.return_value = ReportListRead(project_id=_uuid(10), total=0, reports=[])
    return mock


class TestEvaluationToolsRegistered:
    def test_evaluation_tools_present(self) -> None:
        reg = ToolRegistry()
        names = set(reg.registry.keys())
        for expected in {
            "get_evaluation_results",
            "evaluate_run",
            "create_evaluation_cases",
            "compare_results",
            "generate_report",
            "list_report_runs",
        }:
            assert expected in names

    def test_write_classification(self) -> None:
        reg = ToolRegistry()
        for name in {"evaluate_run", "create_evaluation_cases", "generate_report"}:
            assert reg.is_mutating(name) is True, name
            assert reg.is_destructive(name) is False, name
        for name in {"get_evaluation_results", "compare_results", "list_report_runs"}:
            assert reg.is_mutating(name) is False, name


class TestGetEvaluationResultsTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "get_evaluation_results", client, {"project_id": PROJECT, "execution_id": EXEC1}
        )
        client.get_evaluation_results.assert_called_once_with(PROJECT, EXEC1)
        assert result.ok is True
        assert "2/3 passed" in result.summary

    def test_missing_id_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("get_evaluation_results", _mock_client(), {"project_id": PROJECT})
        assert result.ok is False
        assert result.error


class TestEvaluateRunTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("evaluate_run", client, {"project_id": PROJECT, "execution_id": EXEC1})
        client.enqueue_evaluation.assert_called_once_with(PROJECT, EXEC1)
        assert result.ok is True
        assert "enqueued" in result.summary.lower()


class TestCreateEvaluationCasesTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "create_evaluation_cases",
            client,
            {
                "project_id": PROJECT,
                "dataset_id": DATASET,
                "evaluation_cases": [
                    {
                        "task_id": EXEC1,
                        "test_case_id": EXEC2,
                        "expected_answer": "42",
                        "evaluation_method": "exact_match",
                    }
                ],
            },
        )
        client.create_evaluation_cases.assert_called_once()
        args = client.create_evaluation_cases.call_args[0]
        assert args[0] == PROJECT
        assert args[1] == DATASET
        assert isinstance(args[2], list) and len(args[2]) == 1
        assert result.ok is True


class TestCompareResultsTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "compare_results",
            client,
            {"project_id": PROJECT, "execution_ids": [EXEC1, EXEC2]},
        )
        client.compare_executions.assert_called_once_with(PROJECT, [EXEC1, EXEC2])
        assert result.ok is True
        assert result.data["leaderboard"][0]["rank"] == 1


class TestGenerateReportTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "generate_report",
            client,
            {"project_id": PROJECT, "title": "Q1 Report", "execution_id": EXEC1},
        )
        client.generate_report.assert_called_once_with(
            PROJECT,
            "Q1 Report",
            benchmark_id=None,
            execution_id=EXEC1,
            version_string=None,
        )
        assert result.ok is True
        assert "Q1 Report" in result.summary


class TestListReportRunsTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("list_report_runs", client, {"project_id": PROJECT})
        client.list_reports.assert_called_once_with(PROJECT)
        assert result.ok is True
        assert "0 report" in result.summary or "report(s)" in result.summary


class TestEvaluationWriteConfirms:
    def test_write_tools_prompt_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[bool] = []

        def fake_confirm(_msg: str, default: bool = False) -> bool:
            calls.append(default)
            return True

        monkeypatch.setattr("cli.agent.repl.click.confirm", fake_confirm)
        provider = MagicMock()
        provider.generate.return_value = MagicMock(content="", function_calls=[], text="done")
        repl = AgentREPL(
            provider=provider,
            client=_mock_client(),
            registry=ToolRegistry(),
            confirm=None,
            echo=lambda s: None,
        )
        assert (
            repl._prompt_confirm("evaluate_run", {"project_id": PROJECT, "execution_id": EXEC1})
            is True
        )
        assert len(calls) == 1
