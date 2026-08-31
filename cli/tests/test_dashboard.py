"""Tests for `atlas dashboard`.

Mocks at the SDK boundary (``AtlasClient``) so no live backend is required.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from atlas_sdk.models.dashboard import (
    DashboardActivity,
    DashboardCapability,
    DashboardCapabilityScore,
    DashboardHierarchy,
    DashboardItem,
    DashboardRuntime,
    DashboardSnapshot,
    DashboardSummary,
)
from click.testing import CliRunner

from cli.app import main


def _snapshot() -> DashboardSnapshot:
    summary = DashboardSummary(
        active_runs_count=6,
        queued_runs_count=6,
        completed_runs_count=72,
        failed_runs_count=19,
        cancelled_runs_count=12,
        total_runs_count=115,
    )
    hierarchy = DashboardHierarchy(
        models=17,
        benchmarks=20,
        datasets=14,
        evaluations=54,
        reports=18,
    )
    runtime = DashboardRuntime(
        engine_status="healthy",
        total_benchmarks=20,
        total_evaluations=54,
        total_models=17,
        avg_runtime_sec=37.5,
    )
    jobs = [
        DashboardItem(
            id="b94248f7-f5f9-4ed8-992a-b29751b4e710",
            model="mock",
            benchmark="Python Vulnerability Detection Benchmark",
            status="Completed",
            progress=100,
            is_verified=True,
            source="real",
        ),
        DashboardItem(
            id="5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0",
            model="claude-3",
            benchmark="HumanEval",
            status="Running",
            progress=40,
            is_verified=False,
            source="real",
        ),
    ]
    activity = [
        DashboardActivity(
            id="ex-1",
            type="evaluation_completed",
            title="mock completed on Python Vulnerability Detection Benchmark",
            description="Run b94248f7 finished with 100% progress.",
            timestamp="2026-08-23T07:04:07.219431",
        ),
        DashboardActivity(
            id="report-1",
            type="report_generated",
            title="Report generated: Evaluation Report",
            description="Execution run report Evaluation Report is available.",
            timestamp="2026-08-23T07:05:00.000000",
        ),
    ]
    capability = DashboardCapability(
        model_name="mock",
        provider="Unknown",
        rank=1,
        score=100.0,
        capabilities=[DashboardCapabilityScore(domain="Python", score=100.0)],
    )
    return DashboardSnapshot(
        generated_at=datetime(2026, 8, 28, 6, 34, 32, tzinfo=UTC),
        version="1.0.0",
        summary=summary,
        hierarchy=hierarchy,
        running_jobs=[],
        recent_verified_runs=[jobs[0]],
        active_executions=jobs,
        activity=activity,
        runtime=runtime,
        capability=capability,
    )


def _mock_client(snapshot: DashboardSnapshot | None = None) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_dashboard.return_value = snapshot or _snapshot()
    return mock


def _mock_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_dashboard.side_effect = exc
    return mock


# ── discovery ───────────────────────────────────────────────────────────


def test_dashboard_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "dashboard" in result.output.lower()


def test_dashboard_subcommand_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["dashboard", "--help"])
    assert result.exit_code == 0
    assert "dashboard" in result.output.lower()


# ── human mode ──────────────────────────────────────────────────────────


def test_dashboard_human(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["dashboard"])
    assert result.exit_code == 0
    assert "Atlas Dashboard" in result.output
    assert "Runs" in result.output
    assert "Total:" in result.output
    assert "115" in result.output
    assert "Active:" in result.output
    assert "Queued:" in result.output
    assert "Completed:" in result.output
    assert "Failed:" in result.output
    assert "Cancelled:" in result.output
    assert "Platform" in result.output
    assert "Benchmarks:" in result.output
    assert "Models:" in result.output
    assert "Datasets:" in result.output
    assert "mock" in result.output
    assert "claude-3" in result.output
    assert "100%" in result.output
    assert "mock completed on Python Vulnerability Detection Benchmark" in result.output


def test_dashboard_human_empty_activity(runner: CliRunner) -> None:
    snapshot = _snapshot()
    snapshot.activity = []
    with patch("cli.client.AtlasClient", return_value=_mock_client(snapshot)):
        result = runner.invoke(main, ["dashboard"])
    assert result.exit_code == 0
    assert "(no recent activity)" in result.output


# ── json mode ───────────────────────────────────────────────────────────


def test_dashboard_json_preserves_backend_structure(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--output", "json", "dashboard"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["version"] == "1.0.0"
    assert data["summary"]["total_runs_count"] == 115
    assert data["summary"]["completed_runs_count"] == 72
    assert data["hierarchy"]["benchmarks"] == 20
    assert data["hierarchy"]["models"] == 17
    assert data["runtime"]["avg_runtime_sec"] == 37.5
    assert len(data["active_executions"]) == 2
    assert data["active_executions"][0]["model"] == "mock"
    assert len(data["activity"]) == 2
    assert data["activity"][0]["type"] == "evaluation_completed"
    assert data["capability"]["model_name"] == "mock"
    assert data["capability"]["capabilities"][0]["domain"] == "Python"


# ── quiet mode ──────────────────────────────────────────────────────────


def test_dashboard_quiet(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--quiet", "dashboard"])
    assert result.exit_code == 0
    assert result.output == ""


# ── params ──────────────────────────────────────────────────────────────


def test_dashboard_calls_get_dashboard(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["dashboard"])
    mock.get_dashboard.assert_called_once_with()


# ── errors ──────────────────────────────────────────────────────────────


def test_dashboard_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Unauthorized"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["dashboard"])
    assert result.exit_code == 3


def test_dashboard_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    mock = _mock_client_error(NetworkError(message="Connection refused"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["dashboard"])
    assert result.exit_code == 6


def test_dashboard_json_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Expired token"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["--output", "json", "dashboard"])
    assert result.exit_code == 3
