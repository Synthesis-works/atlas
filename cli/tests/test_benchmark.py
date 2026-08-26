"""Tests for `atlas benchmark list`, `get`, and `versions`.

Mocks at the SDK boundary to test CLI rendering without real HTTP.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

from atlas_sdk.models.benchmarks import (
    BenchmarkRead,
    BenchmarkVersionRead,
    PageResponse,
)
from click.testing import CliRunner

from cli.app import main


def _bench(
    id: str | None = None,
    name: str = "Test Benchmark",
    state: str = "published",
) -> BenchmarkRead:
    return BenchmarkRead(
        id=uuid.UUID(id or "00000000-0000-0000-0000-000000000001"),
        project_id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        state=state,
        name=name,
    )


def _mock_page(
    items: list[BenchmarkRead] | None = None,
    total: int = 2,
) -> PageResponse[BenchmarkRead]:
    if items is None:
        items = [
            _bench(name="Alpha Benchmark"),
            _bench(
                id="00000000-0000-0000-0000-000000000002",
                name="Beta Benchmark",
            ),
        ]
    return PageResponse(items=items, total=total, limit=50)


def _mock_client(
    page: PageResponse[BenchmarkRead] | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_benchmarks.return_value = page or _mock_page()
    return mock


def _mock_client_empty() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_benchmarks.return_value = _mock_page(items=[], total=0)
    return mock


def _mock_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_benchmarks.side_effect = exc
    mock.get_benchmark.side_effect = exc
    return mock


def _mock_client_get(
    benchmark: BenchmarkRead | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_benchmark.return_value = benchmark or _bench()
    return mock


def _mock_client_get_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.get_benchmark.side_effect = exc
    return mock


# ── discovery ───────────────────────────────────────────────────────────


def test_benchmark_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "benchmark" in result.output.lower()


def test_benchmark_list_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["benchmark", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output.lower()


# ── human mode ──────────────────────────────────────────────────────────


def test_benchmark_list_human(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(main, ["benchmark", "list"])
    assert result.exit_code == 0
    assert "Alpha Benchmark" in result.output
    assert "Beta Benchmark" in result.output


def test_benchmark_list_human_empty(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_empty(),
    ):
        result = runner.invoke(main, ["benchmark", "list"])
    assert result.exit_code == 0
    assert "no benchmarks" in result.output.lower()


# ── JSON mode ───────────────────────────────────────────────────────────


def test_benchmark_list_json(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(
            main, ["--output", "json", "benchmark", "list"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "items" in parsed
    assert "total" in parsed
    assert len(parsed["items"]) == 2
    assert parsed["items"][0]["name"] == "Alpha Benchmark"


def test_benchmark_list_json_empty(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_empty(),
    ):
        result = runner.invoke(
            main, ["--output", "json", "benchmark", "list"]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"] == []
    assert parsed["total"] == 0


# ── quiet mode ──────────────────────────────────────────────────────────


def test_benchmark_list_quiet(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(main, ["--quiet", "benchmark", "list"])
    assert result.exit_code == 0
    assert result.output == ""


# ── no token ────────────────────────────────────────────────────────────


def test_benchmark_list_no_token(runner: CliRunner) -> None:
    """Without a token, server returns 401 → auth error (exit 3)."""
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(main, ["benchmark", "list"])
    assert result.exit_code == 3


def test_benchmark_list_no_token_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main, ["--output", "json", "benchmark", "list"]
        )
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 401


# ── SDK error ───────────────────────────────────────────────────────────


def test_benchmark_list_sdk_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main, ["--output", "json", "benchmark", "list"]
        )
    assert result.exit_code == 6
    parsed = json.loads(result.output)
    assert "error" in parsed


# ── get: discovery ──────────────────────────────────────────────────────


def test_benchmark_get_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["benchmark", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output.lower()


# ── get: human mode ─────────────────────────────────────────────────────


def test_benchmark_get_human(runner: CliRunner) -> None:
    bench = _bench(name="My Benchmark")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_get(bench),
    ):
        result = runner.invoke(
            main, ["benchmark", "get", str(bench.id)]
        )
    assert result.exit_code == 0
    assert "My Benchmark" in result.output
    assert str(bench.id) in result.output


# ── get: JSON mode ──────────────────────────────────────────────────────


def test_benchmark_get_json(runner: CliRunner) -> None:
    bench = _bench(name="JSON Bench")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_get(bench),
    ):
        result = runner.invoke(
            main, ["--output", "json", "benchmark", "get", str(bench.id)]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["name"] == "JSON Bench"
    assert parsed["id"] == str(bench.id)
    assert parsed["state"] == "published"


# ── get: quiet mode ─────────────────────────────────────────────────────


def test_benchmark_get_quiet(runner: CliRunner) -> None:
    bench = _bench()
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_get(bench),
    ):
        result = runner.invoke(
            main, ["--quiet", "benchmark", "get", str(bench.id)]
        )
    assert result.exit_code == 0
    assert result.output == ""


# ── get: not found ──────────────────────────────────────────────────────


def test_benchmark_get_not_found(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="Benchmark not found")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_get_error(err),
    ):
        result = runner.invoke(
            main, ["benchmark", "get", "00000000-0000-0000-0000-000000000042"]
        )
    assert result.exit_code == 5


def test_benchmark_get_not_found_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="Benchmark not found")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_get_error(err),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "benchmark", "get",
             "00000000-0000-0000-0000-000000000042"],
        )
    assert result.exit_code == 5
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 404


# ── get: auth error ─────────────────────────────────────────────────────


def test_benchmark_get_no_token(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_get_error(err),
    ):
        result = runner.invoke(
            main, ["benchmark", "get", "00000000-0000-0000-0000-000000000001"]
        )
    assert result.exit_code == 3


# ── get: network error ──────────────────────────────────────────────────


def test_benchmark_get_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_get_error(err),
    ):
        result = runner.invoke(
            main, ["benchmark", "get", "00000000-0000-0000-0000-000000000001"]
        )
    assert result.exit_code == 6


def test_benchmark_get_network_error_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_get_error(err),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "benchmark", "get",
             "00000000-0000-0000-0000-000000000001"],
        )
    assert result.exit_code == 6
    parsed = json.loads(result.output)
    assert "error" in parsed


# ── versions helpers ────────────────────────────────────────────────────

BENCH_ID = "00000000-0000-0000-0000-000000000001"


def _version(
    version_string: str = "1.0.0",
    state: str = "published",
) -> BenchmarkVersionRead:
    return BenchmarkVersionRead(
        id=uuid.uuid4(),
        benchmark_id=uuid.UUID(BENCH_ID),
        version_string=version_string,
        state=state,
    )


def _mock_client_versions(
    versions: list[BenchmarkVersionRead] | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_benchmark_versions.return_value = versions or [
        _version("1.0.0", "published"),
        _version("2.0.0", "draft"),
    ]
    return mock


def _mock_client_versions_empty() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_benchmark_versions.return_value = []
    return mock


def _mock_client_versions_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_benchmark_versions.side_effect = exc
    return mock


# ── versions: discovery ─────────────────────────────────────────────────


def test_benchmark_versions_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["benchmark", "--help"])
    assert result.exit_code == 0
    assert "versions" in result.output.lower()


# ── versions: human mode ────────────────────────────────────────────────


def test_benchmark_versions_human(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions(),
    ):
        result = runner.invoke(
            main, ["benchmark", "versions", BENCH_ID]
        )
    assert result.exit_code == 0
    assert "1.0.0" in result.output
    assert "2.0.0" in result.output


def test_benchmark_versions_human_empty(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions_empty(),
    ):
        result = runner.invoke(
            main, ["benchmark", "versions", BENCH_ID]
        )
    assert result.exit_code == 0
    assert "no versions" in result.output.lower()


# ── versions: JSON mode ─────────────────────────────────────────────────


def test_benchmark_versions_json(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions(),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "benchmark", "versions", BENCH_ID],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "items" in parsed
    assert "total" in parsed
    assert len(parsed["items"]) == 2
    assert parsed["items"][0]["version_string"] == "1.0.0"


def test_benchmark_versions_json_empty(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions_empty(),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "benchmark", "versions", BENCH_ID],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"] == []
    assert parsed["total"] == 0


# ── versions: quiet mode ────────────────────────────────────────────────


def test_benchmark_versions_quiet(runner: CliRunner) -> None:
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions(),
    ):
        result = runner.invoke(
            main, ["--quiet", "benchmark", "versions", BENCH_ID]
        )
    assert result.exit_code == 0
    assert result.output == ""


# ── versions: 404 ───────────────────────────────────────────────────────


def test_benchmark_versions_not_found(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="Benchmark not found")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions_error(err),
    ):
        result = runner.invoke(
            main, ["benchmark", "versions", BENCH_ID]
        )
    assert result.exit_code == 5


def test_benchmark_versions_not_found_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="Benchmark not found")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions_error(err),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "benchmark", "versions", BENCH_ID],
        )
    assert result.exit_code == 5
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 404


# ── versions: auth error ────────────────────────────────────────────────


def test_benchmark_versions_no_token(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions_error(err),
    ):
        result = runner.invoke(
            main, ["benchmark", "versions", BENCH_ID]
        )
    assert result.exit_code == 3


# ── versions: network error ─────────────────────────────────────────────


def test_benchmark_versions_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions_error(err),
    ):
        result = runner.invoke(
            main, ["benchmark", "versions", BENCH_ID]
        )
    assert result.exit_code == 6


def test_benchmark_versions_network_error_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.benchmark.AtlasClient",
        return_value=_mock_client_versions_error(err),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "benchmark", "versions", BENCH_ID],
        )
    assert result.exit_code == 6
    parsed = json.loads(result.output)
    assert "error" in parsed
