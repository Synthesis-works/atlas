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
    ModelSummary,
    TrendPoint,
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
    with patch("cli.client.AtlasClient", return_value=_mock_client(leaderboard)):
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
    with patch("cli.client.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert "(no entries)" in result.output


def test_leaderboard_benchmark_human_pagination_hint(runner: CliRunner) -> None:
    leaderboard = _leaderboard(items=[_entry()], total=50)
    with patch("cli.client.AtlasClient", return_value=_mock_client(leaderboard)):
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
    with patch("cli.client.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert "-2" in result.output


# ── json mode ───────────────────────────────────────────────────────────


def test_leaderboard_benchmark_json_preserves_backend_structure(runner: CliRunner) -> None:
    leaderboard = _leaderboard()
    with patch("cli.client.AtlasClient", return_value=_mock_client(leaderboard)):
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
    with patch("cli.client.AtlasClient", return_value=_mock_client(leaderboard)):
        result = runner.invoke(main, ["--output", "json", "leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["entries"]["items"] == []
    assert data["entries"]["total"] == 0


# ── quiet mode ──────────────────────────────────────────────────────────


def test_leaderboard_benchmark_quiet(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--quiet", "leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert result.output == ""


def test_leaderboard_benchmark_quiet_via_shorthand(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["-q", "leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 0
    assert result.output == ""


# ── params ──────────────────────────────────────────────────────────────


def test_leaderboard_benchmark_default_params(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    mock.get_benchmark_leaderboard.assert_called_once_with(_BV_ID, limit=20, offset=0)


def test_leaderboard_benchmark_pagination_params(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["leaderboard", "benchmark", _BV_ID, "--limit", "10", "--offset", "5"])
    mock.get_benchmark_leaderboard.assert_called_once_with(_BV_ID, limit=10, offset=5)


def test_leaderboard_benchmark_requires_version_id(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "benchmark"])
    assert result.exit_code == 2


# ── errors ──────────────────────────────────────────────────────────────


def test_leaderboard_benchmark_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Unauthorized"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 3


def test_leaderboard_benchmark_403(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    mock = _mock_client_error(ForbiddenError(status=403, message="Forbidden"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 4


def test_leaderboard_benchmark_404(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    mock = _mock_client_error(NotFoundError(status=404, message="Not found"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 5


def test_leaderboard_benchmark_422(runner: CliRunner) -> None:
    from atlas_sdk.errors import ValidationError

    mock = _mock_client_error(ValidationError(status=422, message="Invalid parameters"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 7


def test_leaderboard_benchmark_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    mock = _mock_client_error(NetworkError(message="Connection refused"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 6


def test_leaderboard_benchmark_server_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ServerError

    mock = _mock_client_error(ServerError(status=500, message="Internal error"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 1


def test_leaderboard_benchmark_json_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Expired token"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["--output", "json", "leaderboard", "benchmark", _BV_ID])
    assert result.exit_code == 3


# -- model command -------------------------------------------------------


def _summary(
    *,
    model: str = "mock",
    benchmarks: int = 4,
    best_rank: int | None = 1,
    average_rank: float | None = 1.5,
    average_score: float | None = 85.71428571428571,
    last_execution: datetime | None = None,
    latest_delta: int | None = None,
) -> ModelSummary:
    if last_execution is None and benchmarks > 0:
        last_execution = datetime(2026, 8, 23, 7, 4, 7, microsecond=219431)
    return ModelSummary(
        model=model,
        benchmarks=benchmarks,
        best_rank=best_rank,
        average_rank=average_rank,
        average_score=average_score,
        last_execution=last_execution,
        latest_delta=latest_delta,
    )


def _mock_summary_client(summary: ModelSummary | None = None) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_model_summary.return_value = summary or _summary()
    return mock


def _mock_summary_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_model_summary.side_effect = exc
    return mock


def test_leaderboard_model_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "--help"])
    assert result.exit_code == 0
    assert "model" in result.output.lower()


def test_leaderboard_model_subcommand_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "model", "--help"])
    assert result.exit_code == 0
    assert "MODEL_NAME" in result.output


def test_leaderboard_model_human(runner: CliRunner) -> None:
    summary = _summary(latest_delta=2)
    with patch("cli.client.AtlasClient", return_value=_mock_summary_client(summary)):
        result = runner.invoke(main, ["leaderboard", "model", "mock"])
    assert result.exit_code == 0
    assert "Model Summary" in result.output
    assert "Model:  mock" in result.output
    assert "Benchmarks:  4" in result.output
    assert "Best Rank:  1" in result.output
    assert "Avg Rank:  1.50" in result.output
    assert "Avg Score:  85.71" in result.output
    assert "2026-08-23 07:04" in result.output
    assert "Delta:  +2" in result.output


def test_leaderboard_model_human_omits_null_fields(runner: CliRunner) -> None:
    summary = _summary(
        best_rank=None,
        average_rank=None,
        average_score=None,
        last_execution=None,
        latest_delta=None,
    )
    with patch("cli.client.AtlasClient", return_value=_mock_summary_client(summary)):
        result = runner.invoke(main, ["leaderboard", "model", "mock"])
    assert result.exit_code == 0
    assert "Model Summary" in result.output
    assert "Benchmarks:  4" in result.output
    assert "Best Rank" not in result.output
    assert "Avg Rank" not in result.output
    assert "Avg Score" not in result.output
    assert "Delta" not in result.output


def test_leaderboard_model_human_unknown(runner: CliRunner) -> None:
    summary = _summary(
        model="nope",
        benchmarks=0,
        best_rank=None,
        average_rank=None,
        average_score=None,
        last_execution=None,
        latest_delta=None,
    )
    with patch("cli.client.AtlasClient", return_value=_mock_summary_client(summary)):
        result = runner.invoke(main, ["leaderboard", "model", "nope"])
    assert result.exit_code == 0
    assert "No benchmark data for model 'nope'" in result.output


def test_leaderboard_model_json_preserves_backend_structure(runner: CliRunner) -> None:
    summary = _summary(latest_delta=2)
    with patch("cli.client.AtlasClient", return_value=_mock_summary_client(summary)):
        result = runner.invoke(main, ["--output", "json", "leaderboard", "model", "mock"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["model"] == "mock"
    assert data["benchmarks"] == 4
    assert data["best_rank"] == 1
    assert data["average_rank"] == 1.5
    assert data["average_score"] == 85.71428571428571
    assert data["last_execution"] == "2026-08-23T07:04:07.219431"
    assert data["latest_delta"] == 2


def test_leaderboard_model_json_unknown_preserves_nulls(runner: CliRunner) -> None:
    summary = _summary(
        model="nope",
        benchmarks=0,
        best_rank=None,
        average_rank=None,
        average_score=None,
        last_execution=None,
        latest_delta=None,
    )
    with patch("cli.client.AtlasClient", return_value=_mock_summary_client(summary)):
        result = runner.invoke(main, ["--output", "json", "leaderboard", "model", "nope"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["model"] == "nope"
    assert data["benchmarks"] == 0
    assert data["best_rank"] is None
    assert data["average_rank"] is None
    assert data["average_score"] is None
    assert data["last_execution"] is None
    assert data["latest_delta"] is None


def test_leaderboard_model_quiet(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_summary_client()):
        result = runner.invoke(main, ["--quiet", "leaderboard", "model", "mock"])
    assert result.exit_code == 0
    assert result.output == ""


def test_leaderboard_model_quiet_via_shorthand(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_summary_client()):
        result = runner.invoke(main, ["-q", "leaderboard", "model", "mock"])
    assert result.exit_code == 0
    assert result.output == ""


def test_leaderboard_model_passes_model_name(runner: CliRunner) -> None:
    mock = _mock_summary_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["leaderboard", "model", "mock"])
    mock.get_model_summary.assert_called_once_with("mock")


def test_leaderboard_model_requires_model_name(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "model"])
    assert result.exit_code == 2


def test_leaderboard_model_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_summary_client_error(AuthError(status=401, message="Unauthorized"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock"])
    assert result.exit_code == 3


def test_leaderboard_model_403(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    mock = _mock_summary_client_error(ForbiddenError(status=403, message="Forbidden"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock"])
    assert result.exit_code == 4


def test_leaderboard_model_404(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    mock = _mock_summary_client_error(NotFoundError(status=404, message="Not found"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock"])
    assert result.exit_code == 5


def test_leaderboard_model_422(runner: CliRunner) -> None:
    from atlas_sdk.errors import ValidationError

    mock = _mock_summary_client_error(ValidationError(status=422, message="Invalid parameters"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock"])
    assert result.exit_code == 7


def test_leaderboard_model_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    mock = _mock_summary_client_error(NetworkError(message="Connection refused"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock"])
    assert result.exit_code == 6


def test_leaderboard_model_server_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ServerError

    mock = _mock_summary_client_error(ServerError(status=500, message="Internal error"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock"])
    assert result.exit_code == 1


def test_leaderboard_model_json_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_summary_client_error(AuthError(status=401, message="Expired token"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["--output", "json", "leaderboard", "model", "mock"])
    assert result.exit_code == 3


# -- model --history ------------------------------------------------------


def _point(
    *,
    timestamp: str = "2026-08-17T16:25:46.342572",
    score: float = 0.0,
    rank: int | None = None,
    benchmark_version: str | None = "15f01fef-bd6c-457c-a041-101dbc6c8740",
    execution_id: str = "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0",
) -> TrendPoint:
    from datetime import datetime

    return TrendPoint(
        timestamp=datetime.fromisoformat(timestamp),
        score=score,
        rank=rank,
        benchmark_version=benchmark_version,
        execution_id=execution_id,
    )


def _mock_history_client(points: list[TrendPoint] | None = None) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_model_history.return_value = [] if points is None else points
    return mock


def _mock_history_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_model_history.side_effect = exc
    return mock


def test_leaderboard_model_history_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "model", "--help"])
    assert result.exit_code == 0
    assert "--history" in result.output


def test_leaderboard_model_history_human(runner: CliRunner) -> None:
    points = [
        _point(),
        _point(
            timestamp="2026-08-23T07:04:07.219431",
            score=100.0,
            rank=2,
            benchmark_version="181d1c91-15f9-43e7-866d-33809aaaedf1",
            execution_id="b94248f7-f5f9-4ed8-992a-b29751b4e710",
        ),
    ]
    with patch("cli.client.AtlasClient", return_value=_mock_history_client(points)):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 0
    assert "Model History: mock" in result.output
    assert "Timestamp" in result.output
    assert "2026-08-17 16:25" in result.output
    assert "0.00" in result.output
    assert "100.00" in result.output
    assert "2" in result.output
    assert "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0" in result.output
    assert "b94248f7-f5f9-4ed8-992a-b29751b4e710" in result.output


def test_leaderboard_model_history_human_empty(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_history_client([])):
        result = runner.invoke(main, ["leaderboard", "model", "nope", "--history"])
    assert result.exit_code == 0
    assert "No history for model 'nope'" in result.output


def test_leaderboard_model_history_json_preserves_backend_structure(runner: CliRunner) -> None:
    points = [
        _point(timestamp="2026-08-23T07:04:07.219431", score=100.0, rank=None),
        _point(
            timestamp="2026-08-23T07:05:00.000000",
            score=99.5,
            rank=2,
            benchmark_version=None,
            execution_id="abc",
        ),
    ]
    with patch("cli.client.AtlasClient", return_value=_mock_history_client(points)):
        result = runner.invoke(
            main, ["--output", "json", "leaderboard", "model", "mock", "--history"]
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["timestamp"] == "2026-08-23T07:04:07.219431"
    assert data[0]["score"] == 100.0
    assert data[0]["rank"] is None
    assert data[0]["benchmark_version"] == "15f01fef-bd6c-457c-a041-101dbc6c8740"
    assert data[0]["execution_id"] == "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0"
    assert data[1]["benchmark_version"] is None
    assert data[1]["execution_id"] == "abc"


def test_leaderboard_model_history_quiet(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_history_client()):
        result = runner.invoke(main, ["--quiet", "leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 0
    assert result.output == ""


def test_leaderboard_model_history_quiet_via_shorthand(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_history_client()):
        result = runner.invoke(main, ["-q", "leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 0
    assert result.output == ""


def test_leaderboard_model_history_passes_model_name(runner: CliRunner) -> None:
    mock = _mock_history_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["leaderboard", "model", "mock", "--history"])
    mock.get_model_history.assert_called_once_with("mock")


def test_leaderboard_model_history_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_history_client_error(AuthError(status=401, message="Unauthorized"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 3


def test_leaderboard_model_history_403(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    mock = _mock_history_client_error(ForbiddenError(status=403, message="Forbidden"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 4


def test_leaderboard_model_history_404(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    mock = _mock_history_client_error(NotFoundError(status=404, message="Not found"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 5


def test_leaderboard_model_history_422(runner: CliRunner) -> None:
    from atlas_sdk.errors import ValidationError

    mock = _mock_history_client_error(ValidationError(status=422, message="Invalid params"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 7


def test_leaderboard_model_history_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    mock = _mock_history_client_error(NetworkError(message="Connection refused"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 6


def test_leaderboard_model_history_server_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ServerError

    mock = _mock_history_client_error(ServerError(status=500, message="Internal error"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--history"])
    assert result.exit_code == 1


def test_leaderboard_model_history_json_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_history_client_error(AuthError(status=401, message="Expired token"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(
            main, ["--output", "json", "leaderboard", "model", "mock", "--history"]
        )
    assert result.exit_code == 3


# -- model --benchmarks ----------------------------------------------------


def _bench_history(
    *,
    benchmark_name: str,
    versions: list[tuple[str, list[TrendPoint]]],
) -> dict:
    from atlas_sdk.models.leaderboard import (
        ModelBenchmarkHistory,
        ModelBenchmarkVersionHistory,
    )

    version_objs = [
        ModelBenchmarkVersionHistory(version_string=v, history=points) for v, points in versions
    ]
    return ModelBenchmarkHistory(benchmark_name=benchmark_name, versions=version_objs)


def _mock_benchmarks_client(
    entries: list | None = None,
    model_name: str = "mock",
) -> MagicMock:
    if entries is None:
        entries = [
            _bench_history(
                benchmark_name="Python Vulnerability Detection Benchmark",
                versions=[
                    (
                        "1.0.0",
                        [
                            _point(timestamp="2026-08-17T16:25:46.342572", score=0.0),
                            _point(
                                timestamp="2026-08-23T07:04:07.219431",
                                score=100.0,
                                execution_id="b94248f7-f5f9-4ed8-992a-b29751b4e710",
                            ),
                        ],
                    )
                ],
            ),
            _bench_history(
                benchmark_name="HumanEval",
                versions=[
                    (
                        "1.0.0",
                        [
                            _point(
                                timestamp="2026-08-23T06:51:00.548071",
                                score=88.5,
                            )
                        ],
                    ),
                    (
                        "1.1.0",
                        [
                            _point(
                                timestamp="2026-08-23T06:52:51.933846",
                                score=92.0,
                            ),
                            _point(
                                timestamp="2026-08-23T06:55:00.000000",
                                score=95.0,
                            ),
                        ],
                    ),
                ],
            ),
        ]
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_model_benchmarks.return_value = entries
    return mock


def _mock_benchmarks_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_model_benchmarks.side_effect = exc
    return mock


def test_leaderboard_model_benchmarks_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["leaderboard", "model", "--help"])
    assert result.exit_code == 0
    assert "--benchmarks" in result.output


def test_leaderboard_model_benchmarks_human(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_benchmarks_client()):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--benchmarks"])
    assert result.exit_code == 0
    assert "Model Benchmarks: mock" in result.output
    # entries are sorted by benchmark name: HumanEval before Python...
    human_idx = result.output.index("HumanEval")
    python_idx = result.output.index("Python Vulnerability Detection Benchmark")
    assert human_idx < python_idx
    assert "3" in result.output  # HumanEval totals 3 runs
    assert "2" in result.output  # HumanEval has 2 versions
    assert "95.00" in result.output  # HumanEval latest score
    assert "2026-08-23 06:55" in result.output
    assert "100.00" in result.output  # Python benchmark latest score
    assert "2026-08-23 07:04" in result.output


def test_leaderboard_model_benchmarks_human_empty(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_benchmarks_client([])):
        result = runner.invoke(main, ["leaderboard", "model", "nope", "--benchmarks"])
    assert result.exit_code == 0
    assert "No benchmark data for model 'nope'" in result.output


def test_leaderboard_model_benchmarks_json_preserves_backend_structure(
    runner: CliRunner,
) -> None:
    entries = [
        _bench_history(
            benchmark_name="HumanEval",
            versions=[
                (
                    "1.0.0",
                    [
                        _point(
                            timestamp="2026-08-23T06:51:00.548071",
                            score=88.5,
                        )
                    ],
                )
            ],
        )
    ]
    with patch(
        "cli.client.AtlasClient",
        return_value=_mock_benchmarks_client(entries),
    ):
        result = runner.invoke(
            main, ["--output", "json", "leaderboard", "model", "mock", "--benchmarks"]
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["benchmark_name"] == "HumanEval"
    assert data[0]["versions"][0]["version_string"] == "1.0.0"
    point = data[0]["versions"][0]["history"][0]
    assert point["score"] == 88.5
    assert point["timestamp"] == "2026-08-23T06:51:00.548071"
    assert point["execution_id"] == "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0"


def test_leaderboard_model_benchmarks_quiet(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_benchmarks_client()):
        result = runner.invoke(main, ["--quiet", "leaderboard", "model", "mock", "--benchmarks"])
    assert result.exit_code == 0
    assert result.output == ""


def test_leaderboard_model_benchmarks_passes_model_name(runner: CliRunner) -> None:
    mock = _mock_benchmarks_client()
    with patch("cli.client.AtlasClient", return_value=mock):
        runner.invoke(main, ["leaderboard", "model", "mock", "--benchmarks"])
    mock.get_model_benchmarks.assert_called_once_with("mock")


def test_leaderboard_model_history_and_benchmarks_mutually_exclusive(
    runner: CliRunner,
) -> None:
    result = runner.invoke(main, ["leaderboard", "model", "mock", "--history", "--benchmarks"])
    assert result.exit_code == 2


def test_leaderboard_model_benchmarks_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_benchmarks_client_error(AuthError(status=401, message="Unauthorized"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--benchmarks"])
    assert result.exit_code == 3


def test_leaderboard_model_benchmarks_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    mock = _mock_benchmarks_client_error(NetworkError(message="Connection refused"))
    with patch("cli.client.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["leaderboard", "model", "mock", "--benchmarks"])
    assert result.exit_code == 6
