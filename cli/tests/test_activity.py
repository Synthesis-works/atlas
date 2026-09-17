"""Tests for `atlas activity`.

Mocks at the SDK boundary (``AtlasClient``) so no live backend is required.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from atlas_sdk.models.benchmarks import BenchmarkRead
from atlas_sdk.models.executions import ExecutionState
from atlas_sdk.models.history import ExecutionHistoryRead, ModelActivityRead
from click.testing import CliRunner

from cli.app import main


def _benchmarks() -> list[BenchmarkRead]:
    return [
        BenchmarkRead(
            id=uuid.UUID("c711da4c-dbe9-4b37-a94f-0590ade5d01b"),
            project_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            state="published",
            name="SWE-Bench Lite",
        ),
        BenchmarkRead(
            id=uuid.UUID("dcf3c884-0c3c-4507-94a7-880857046fac"),
            project_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            state="published",
            name="TruthfulQA",
        ),
    ]


def _executions() -> list[ExecutionHistoryRead]:
    return [
        ExecutionHistoryRead(
            id="ff0a7a03-ca03-4b67-bc47-eae9335ad6e8",
            benchmark_name="HellaSwag",
            target_model="gemini-2.5-flash",
            status=ExecutionState.FAILED,
            started_at=datetime(2026, 8, 26, 6, 24, 31, 588819, tzinfo=UTC),
            completed_at=datetime(2026, 8, 26, 6, 24, 39, 671965, tzinfo=UTC),
            duration=8083,
            project_id="00000000-0000-0000-0000-000000000003",
        ),
        ExecutionHistoryRead(
            id="89832d92-424c-459e-b8f7-5a8d0e22be24",
            benchmark_name="MBPP",
            target_model="gemini-2.0-flash",
            status=ExecutionState.COMPLETED,
            started_at=datetime(2026, 8, 26, 2, 16, 44, 457915, tzinfo=UTC),
            completed_at=datetime(2026, 8, 26, 2, 16, 57, 457915, tzinfo=UTC),
            duration=13000,
            project_id="33333333-3333-3333-3333-333333333333",
        ),
    ]


def _models() -> list[ModelActivityRead]:
    return [
        ModelActivityRead(
            name="gemini-2.5-flash",
            last_executed_at=datetime(2026, 8, 26, 6, 24, 30, 396401, tzinfo=UTC),
            execution_count=1,
        ),
        ModelActivityRead(
            name="gemini-1.5-pro",
            last_executed_at=datetime(2026, 8, 26, 3, 16, 42, 457915, tzinfo=UTC),
            execution_count=12,
        ),
    ]


def _mock_client() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_recent_benchmarks.return_value = _benchmarks()
    mock.get_recent_executions.return_value = _executions()
    mock.get_recent_models.return_value = _models()
    return mock


def _mock_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_recent_benchmarks.side_effect = exc
    mock.get_recent_executions.side_effect = exc
    mock.get_recent_models.side_effect = exc
    return mock


# ── discovery ───────────────────────────────────────────────────────────


def test_activity_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "activity" in result.output.lower()


def test_activity_subcommand_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["activity", "--help"])
    assert result.exit_code == 0
    assert "--type" in result.output
    assert "--limit" in result.output


def test_activity_invalid_type(runner: CliRunner) -> None:
    result = runner.invoke(main, ["activity", "--type", "bogus"])
    assert result.exit_code == 2


# ── human mode ──────────────────────────────────────────────────────────


def test_activity_human_all_sections(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["activity"])
    assert result.exit_code == 0
    assert "Recent Activity" in result.output
    assert "SWE-Bench Lite" in result.output
    assert "TruthfulQA" in result.output
    assert "gemini-2.5-flash" in result.output
    assert "gemini-1.5-pro" in result.output
    assert "HellaSwag" in result.output
    assert "FAILED" in result.output
    assert "2026-08-26 06:24" in result.output


def test_activity_human_filtered_type(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["activity", "--type", "executions"])
    assert result.exit_code == 0
    assert "Executions" in result.output
    assert "gemini-2.5-flash" in result.output
    assert "SWE-Bench Lite" not in result.output
    assert "Models" not in result.output


def test_activity_human_empty(runner: CliRunner) -> None:
    mock = _mock_client()
    mock.get_recent_benchmarks.return_value = []
    mock.get_recent_executions.return_value = []
    mock.get_recent_models.return_value = []
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["activity"])
    assert result.exit_code == 0
    assert "no recent" in result.output.lower()


# ── json mode ───────────────────────────────────────────────────────────


def test_activity_json_all_sections(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--output", "json", "activity"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["benchmarks"]) == 2
    assert data["benchmarks"][0]["name"] == "SWE-Bench Lite"
    assert data["benchmarks"][0]["state"] == "published"
    assert len(data["executions"]) == 2
    assert data["executions"][0]["target_model"] == "gemini-2.5-flash"
    assert data["executions"][0]["status"] == "FAILED"
    assert data["executions"][0]["duration"] == 8083
    assert len(data["models"]) == 2
    assert data["models"][0]["name"] == "gemini-2.5-flash"
    assert data["models"][0]["execution_count"] == 1


def test_activity_json_filtered_type(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--output", "json", "activity", "--type", "benchmarks"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "benchmarks" in data
    assert "executions" not in data
    assert "models" not in data


# ── quiet mode ──────────────────────────────────────────────────────────


def test_activity_quiet(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--quiet", "activity"])
    assert result.exit_code == 0
    assert result.output == ""


# ── params ──────────────────────────────────────────────────────────────


def test_activity_passes_default_limit(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["activity"])
    mock.get_recent_benchmarks.assert_called_once_with(limit=10)
    mock.get_recent_executions.assert_called_once_with(limit=10)
    mock.get_recent_models.assert_called_once_with(limit=10)


def test_activity_passes_explicit_limit(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["activity", "--limit", "3"])
    mock.get_recent_benchmarks.assert_called_once_with(limit=3)


def test_activity_filtered_type_skips_other_calls(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["activity", "--type", "models"])
    mock.get_recent_models.assert_called_once_with(limit=10)
    mock.get_recent_benchmarks.assert_not_called()
    mock.get_recent_executions.assert_not_called()


# ── errors ──────────────────────────────────────────────────────────────


def test_activity_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Unauthorized"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["activity"])
    assert result.exit_code == 3


def test_activity_json_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Expired token"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["--output", "json", "activity"])
    assert result.exit_code == 3
