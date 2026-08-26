"""Tests for `atlas run submit`.

Mocks at the SDK boundary to test CLI rendering without real HTTP.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from atlas_sdk.models.executions import ExecutionResponse
from click.testing import CliRunner

from cli.app import main


def _exec_response(
    *,
    status: str = "QUEUED",
    target_model: str = "gemini-2.5-flash",
) -> ExecutionResponse:
    return ExecutionResponse(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        benchmark_version_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        status=status,
        target_model=target_model,
        completed_items=0,
        total_items=1,
        started_at=None,
        completed_at=None,
        created_at=datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC),
        created_by=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        max_retries=3,
        attempts=[],
    )


BENCH_VERSION_ID = "22222222-2222-2222-2222-222222222222"


def _mock_client(execution: ExecutionResponse | None = None) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.submit_execution.return_value = execution or _exec_response()
    return mock


def _mock_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.submit_execution.side_effect = exc
    return mock


# ── discovery ───────────────────────────────────────────────────────────


def test_run_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output.lower()


def test_run_submit_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "submit" in result.output.lower()


# ── human mode ──────────────────────────────────────────────────────────


def test_submit_human(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(
            main, ["run", "submit", BENCH_VERSION_ID]
        )
    assert result.exit_code == 0
    assert "11111111-1111-1111-1111-111111111111" in result.output
    assert "QUEUED" in result.output
    assert "gemini-2.5-flash" in result.output


def test_submit_human_custom_model(runner: CliRunner) -> None:
    exec_resp = _exec_response(target_model="gpt-4o")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(exec_resp),
    ):
        result = runner.invoke(
            main,
            ["run", "submit", BENCH_VERSION_ID, "--target-model", "gpt-4o"],
        )
    assert result.exit_code == 0
    assert "gpt-4o" in result.output


# ── JSON mode ───────────────────────────────────────────────────────────


def test_submit_json(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "run", "submit", BENCH_VERSION_ID],
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == "11111111-1111-1111-1111-111111111111"
    assert parsed["status"] == "QUEUED"
    assert parsed["target_model"] == "gemini-2.5-flash"
    assert parsed["benchmark_version_id"] == BENCH_VERSION_ID
    assert parsed["max_retries"] == 3
    assert parsed["attempts"] == []


# ── quiet mode ──────────────────────────────────────────────────────────


def test_submit_quiet(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(
            main, ["--quiet", "run", "submit", BENCH_VERSION_ID]
        )
    assert result.exit_code == 0
    assert result.output == ""


# ── auth error ──────────────────────────────────────────────────────────


def test_submit_no_token(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main, ["run", "submit", BENCH_VERSION_ID]
        )
    assert result.exit_code == 3


def test_submit_no_token_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "run", "submit", BENCH_VERSION_ID],
        )
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 401


# ── forbidden error ─────────────────────────────────────────────────────


def test_submit_forbidden(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    err = ForbiddenError(status=403, message="Forbidden")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main, ["run", "submit", BENCH_VERSION_ID]
        )
    assert result.exit_code == 4


def test_submit_forbidden_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    err = ForbiddenError(status=403, message="Forbidden")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "run", "submit", BENCH_VERSION_ID],
        )
    assert result.exit_code == 4
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 403


# ── not found ───────────────────────────────────────────────────────────


def test_submit_not_found(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="BenchmarkVersion not found")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main, ["run", "submit", "00000000-0000-0000-0000-000000000000"]
        )
    assert result.exit_code == 5


def test_submit_not_found_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="BenchmarkVersion not found")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main,
            [
                "--output", "json", "run", "submit",
                "00000000-0000-0000-0000-000000000000",
            ],
        )
    assert result.exit_code == 5
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 404


# ── validation error ────────────────────────────────────────────────────


def test_submit_validation_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ValidationError

    err = ValidationError(status=422, message="Validation error")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main, ["run", "submit", BENCH_VERSION_ID]
        )
    assert result.exit_code == 7


# ── network error ───────────────────────────────────────────────────────


def test_submit_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main, ["run", "submit", BENCH_VERSION_ID]
        )
    assert result.exit_code == 6


def test_submit_network_error_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "run", "submit", BENCH_VERSION_ID],
        )
    assert result.exit_code == 6
    parsed = json.loads(result.output)
    assert "error" in parsed


# ── server error ────────────────────────────────────────────────────────


def test_submit_server_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ServerError

    err = ServerError(status=500, message="Internal server error")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err),
    ):
        result = runner.invoke(
            main, ["run", "submit", BENCH_VERSION_ID]
        )
    assert result.exit_code == 1
