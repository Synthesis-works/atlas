"""Tests for `atlas leaderboard benchmark`.

Mocks at the SDK boundary to test CLI rendering without real HTTP.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from atlas_sdk.models.benchmarks import PageResponse
from atlas_sdk.models.leaderboard import (
    LeaderboardEntryRead,
    LeaderboardRead,
    LeaderboardType,
)
from click.testing import CliRunner

from cli.app import main

_BV_ID = "181d1c91-15f9-43e7-866d-33809aaaedf1"


def _entry(
    *, rank: int = 1, model_name: str = "mock", score: float = 100.0
) -> LeaderboardEntryRead:
    return LeaderboardEntryRead(
        rank=rank,
        model_name=model_name,
        overall_score=score,
        benchmark_count=1,
        last_updated=datetime(2026, 8, 23, 7, 4, 7, tzinfo=UTC),
        rank_delta=None,
        metadata=None,
    )


def _leaderboard(
    items: list[LeaderboardEntryRead] | None = None,
    *,
    total: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> LeaderboardRead:
    if items is None:
        items = [
            _entry(rank=1, model_name="mock", score=100.0),
            _entry(rank=2, model_name="claude-3", score=88.5),
        ]
    shown = len(items)
    return LeaderboardRead(
        leaderboard_type=LeaderboardType.BENCHMARK,
        title="Benchmark Version 1.0.0",
        description="Leaderboard for Benchmark Version 1.0.0",
        benchmark_version_id=_BV_ID,
        capability_id=None,
        entries=PageResponse[LeaderboardEntryRead](
            items=items,
            total=(total if total is not None else shown),
            limit=limit,
            offset=offset,
            next_cursor=None,
        ),
    )


def _mock_client(leaderboard: LeaderboardRead | None = None) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_benchmark_leaderboard.return_value = leaderboard or _leaderboard()
    return mock


def _mock_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_benchmark_leaderboard.side_effect = exc
    return mock


# ── discovery ───────────────────────────────────────────────────────────


def test_leaderboard_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "leaderboard" in result.output.lower()


def test_leaderboard_benchmark_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "--help"])
    assert result.exit_code == 0
    assert "benchmark" in result.output.lower()


def test_leaderboard_benchmark_subcommand_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "benchmark", "--help"])
    assert result.exit_code == 0
    assert "BENCHMARK_VERSION_ID" in result.output
    assert "--limit" in result.output
    assert "--offset" in result.output


# ── human mode ──────────────────────────────────────────────────────────


def test_leaderboard_benchmark_human(runner: CliRunner) -> None:
    leaderboard = _leaderboard()
    with patch("cli.commands.leaderboard.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert "Benchmark Version 1.0.0" in result.output
    assert "mock" in result.output
    assert "claude-3" in result.output
    assert "100.00" in result.output
    assert "88.50" in result.output
    assert "2026-08-23 07:04" in result.output


def test_leaderboard_benchmark_human_empty(runner: CliRunner) -> None:
    leaderboard = _leaderboard(items=[], total=0)
    with patch("cli.commands.leaderboard.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert "(no entries)" in result.output


def test_leaderboard_benchmark_human_pagination_hint(runner: CliRunner) -> None:
    leaderboard = _leaderboard(items=[_entry()], total=50)
    with patch("cli.commands.leaderboard.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert "Showing 1 of 50" in result.output


def test_leaderboard_benchmark_human_rank_delta(runner: CliRunner) -> None:
    entry = LeaderboardEntryRead(
        rank=1,
        model_name="mock",
        overall_score=88.5,
        benchmark_count=3,
        last_updated=datetime(2026, 8, 23, 7, 4, 7, tzinfo=UTC),
        rank_delta=-2,
        metadata=None,
    )
    leaderboard = _leaderboard(items=[entry])
    with patch("cli.commands.leaderboard.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert "-2" in result.output


# ── json mode ───────────────────────────────────────────────────────────


def test_leaderboard_benchmark_json_preserves_backend_structure(runner: CliRunner) -> None:
    leaderboard = _leaderboard()
    with patch("cli.commands.leaderboard.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["--output", "json", "leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["leaderboard_type"] == "BENCHMARK"
    assert data["title"] == "Benchmark Version 1.0.0"
    assert data["description"] == "Leaderboard for Benchmark Version 1.0.0"
    assert data["benchmark_version_id"] == _BV_ID
    assert data["capability_id"] is None
    assert data["entries"]["total"] == 2
    assert data["entries"]["limit"] == 20
    assert data["entries"]["offset"] == 0
    assert data["entries"]["next_cursor"] is None
    assert len(data["entries"]["items"]) == 2
    item = data["entries"]["items"][0]
    assert item["rank"] == 1
    assert item["model_name"] == "mock"
    assert item["overall_score"] == 100.0
    assert item["benchmark_count"] == 1
    assert item["rank_delta"] is None
    assert item["metadata"] is None


def test_leaderboard_benchmark_json_empty(runner: CliRunner) -> None:
    leaderboard = _leaderboard(items=[], total=0)
    with patch("cli.commands.leaderboard.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["--output", "json", "leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["entries"]["items"] == []
    assert data["entries"]["total"] == 0


# ── quiet mode ──────────────────────────────────────────────────────────


def test_leaderboard_benchmark_quiet(runner: CliRunner) -> None:
    with patch("cli.commands.leaderboard.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--quiet", "leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert result.output == ""


def test_leaderboard_benchmark_quiet_via_shorthand(runner: CliRunner) -> None:
    with patch("cli.commands.leaderboard.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["-q", "leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert result.output == ""


# ── params ──────────────────────────────────────────────────────────────


def test_leaderboard_benchmark_default_params(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    mock.get_benchmark_leaderboard.assert_called_once_with(_BV_ID, limit=20, offset=0)


def test_leaderboard_benchmark_pagination_params(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        runner.invoke(main, [
            "leaderboard", "benchmark", _BV_ID, "--limit", "10", "--offset", "5"
        ])
    mock.get_benchmark_leaderboard.assert_called_once_with(_BV_ID, limit=10, offset=5)


def test_leaderboard_benchmark_requires_version_id(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "benchmark"])
    assert result.exit_code == 2


# ── errors ──────────────────────────────────────────────────────────────


def test_leaderboard_benchmark_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Unauthorized"))
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 3


def test_leaderboard_benchmark_403(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    mock = _mock_client_error(ForbiddenError(status=403, message="Forbidden"))
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 4


def test_leaderboard_benchmark_404(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    mock = _mock_client_error(NotFoundError(status=404, message="Not found"))
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 5


def test_leaderboard_benchmark_422(runner: CliRunner) -> None:
    from atlas_sdk.errors import ValidationError

    mock = _mock_client_error(ValidationError(status=422, message="Invalid parameters"))
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 7


def test_leaderboard_benchmark_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    mock = _mock_client_error(NetworkError(message="Connection refused"))
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 6


def test_leaderboard_benchmark_server_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ServerError

    mock = _mock_client_error(ServerError(status=500, message="Internal error"))
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 1


def test_leaderboard_benchmark_json_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Expired token"))
    with patch("cli.commands.leaderboard.AtlasClient", return_value=mock):
        result = runner.invoke(main, [
            "--output", "json", "leaderboard", "benchmark", _BV_ID
        ])
    assert result.exit_code == 3
