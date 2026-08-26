"""Tests for `atlas run submit`.

Mocks at the SDK boundary to test CLI rendering without real HTTP.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from atlas_sdk.models.executions import ExecutionPage, ExecutionResponse
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


def _mock_client(
    *,
    execution: ExecutionResponse | None = None,
    get_execution: ExecutionResponse | None = None,
    list_executions: list[ExecutionResponse] | None = None,
    total: int | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.submit_execution.return_value = execution or _exec_response()
    mock.get_execution.return_value = get_execution or _exec_response()
    if list_executions is not None:
        items = list_executions
        mock.list_executions.return_value = ExecutionPage(
            items=items,
            total=total if total is not None else len(items),
            limit=20,
            offset=0,
        )
    else:
        mock.list_executions.return_value = ExecutionPage(
            items=[], total=0, limit=20, offset=0,
        )
    return mock


def _mock_client_error(
    exc: Exception, *, method: str = "submit"
) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    if method == "get":
        mock.get_execution.side_effect = exc
    elif method == "list":
        mock.list_executions.side_effect = exc
    else:
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
        return_value=_mock_client(execution=exec_resp),
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


# =====================================================================
# atlas run get
# =====================================================================

EXEC_ID = "11111111-1111-1111-1111-111111111111"


def _exec_response_running() -> ExecutionResponse:
    return ExecutionResponse(
        id=uuid.UUID(EXEC_ID),
        benchmark_version_id=uuid.UUID(BENCH_VERSION_ID),
        status="RUNNING",
        target_model="gemini-2.5-flash",
        completed_items=3,
        total_items=10,
        started_at=datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC),
        completed_at=None,
        created_at=datetime(2026, 8, 26, 11, 55, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 26, 12, 1, 0, tzinfo=UTC),
        created_by=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        max_retries=3,
        attempts=[],
    )


# ── discovery ───────────────────────────────────────────────────────────


def test_run_get_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output.lower()


# ── human mode ──────────────────────────────────────────────────────────


def test_get_human(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(get_execution=_exec_response_running()),
    ):
        result = runner.invoke(main, ["run", "get", EXEC_ID])
    assert result.exit_code == 0
    assert EXEC_ID in result.output
    assert "RUNNING" in result.output
    assert "gemini-2.5-flash" in result.output
    assert "3/10" in result.output


# ── JSON mode ───────────────────────────────────────────────────────────


def test_get_json(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(get_execution=_exec_response_running()),
    ):
        result = runner.invoke(
            main, ["--output", "json", "run", "get", EXEC_ID]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == EXEC_ID
    assert parsed["status"] == "RUNNING"
    assert parsed["completed_items"] == 3
    assert parsed["total_items"] == 10


# ── quiet mode ──────────────────────────────────────────────────────────


def test_get_quiet(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(get_execution=_exec_response_running()),
    ):
        result = runner.invoke(
            main, ["--quiet", "run", "get", EXEC_ID]
        )
    assert result.exit_code == 0
    assert result.output == ""


# ── auth error ──────────────────────────────────────────────────────────


def test_get_no_token(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="get"),
    ):
        result = runner.invoke(main, ["run", "get", EXEC_ID])
    assert result.exit_code == 3


def test_get_no_token_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="get"),
    ):
        result = runner.invoke(
            main, ["--output", "json", "run", "get", EXEC_ID]
        )
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 401


# ── forbidden error ─────────────────────────────────────────────────────


def test_get_forbidden(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    err = ForbiddenError(status=403, message="Forbidden")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="get"),
    ):
        result = runner.invoke(main, ["run", "get", EXEC_ID])
    assert result.exit_code == 4


# ── not found ───────────────────────────────────────────────────────────


def test_get_not_found(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="Execution not found")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="get"),
    ):
        result = runner.invoke(
            main, ["run", "get", "00000000-0000-0000-0000-000000000000"]
        )
    assert result.exit_code == 5


def test_get_not_found_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="Execution not found")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="get"),
    ):
        result = runner.invoke(
            main,
            ["--output", "json", "run", "get", "00000000-0000-0000-0000-000000000000"],
        )
    assert result.exit_code == 5
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 404


# ── network error ───────────────────────────────────────────────────────


def test_get_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="get"),
    ):
        result = runner.invoke(main, ["run", "get", EXEC_ID])
    assert result.exit_code == 6


# ── server error ────────────────────────────────────────────────────────


def test_get_server_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ServerError

    err = ServerError(status=500, message="Internal server error")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="get"),
    ):
        result = runner.invoke(main, ["run", "get", EXEC_ID])
    assert result.exit_code == 1


# =====================================================================
# atlas run list
# =====================================================================


EXEC_ID_2 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _list_items() -> list[ExecutionResponse]:
    return [
        ExecutionResponse(
            id=uuid.UUID(EXEC_ID),
            benchmark_version_id=uuid.UUID(BENCH_VERSION_ID),
            status="COMPLETED",
            target_model="gemini-2.5-flash",
            completed_items=10,
            total_items=10,
            started_at=datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC),
            completed_at=datetime(2026, 8, 26, 12, 5, 0, tzinfo=UTC),
            created_at=datetime(2026, 8, 26, 11, 55, 0, tzinfo=UTC),
            updated_at=datetime(2026, 8, 26, 12, 5, 0, tzinfo=UTC),
            created_by=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            max_retries=3,
            attempts=[],
        ),
        ExecutionResponse(
            id=uuid.UUID(EXEC_ID_2),
            benchmark_version_id=uuid.UUID(BENCH_VERSION_ID),
            status="RUNNING",
            target_model="gpt-4o",
            completed_items=3,
            total_items=10,
            started_at=datetime(2026, 8, 26, 13, 0, 0, tzinfo=UTC),
            completed_at=None,
            created_at=datetime(2026, 8, 26, 12, 55, 0, tzinfo=UTC),
            updated_at=datetime(2026, 8, 26, 13, 1, 0, tzinfo=UTC),
            created_by=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            max_retries=3,
            attempts=[],
        ),
    ]


# ── discovery ───────────────────────────────────────────────────────────


def test_run_list_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output.lower()


# ── human mode ──────────────────────────────────────────────────────────


def test_list_human(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(list_executions=_list_items()),
    ):
        result = runner.invoke(main, ["run", "list"])
    assert result.exit_code == 0
    assert "COMPLETED" in result.output
    assert "RUNNING" in result.output
    assert EXEC_ID[:8] in result.output
    assert EXEC_ID_2[:8] in result.output
    assert "10/10" in result.output
    assert "3/10" in result.output


def test_list_human_empty(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(list_executions=[]),
    ):
        result = runner.invoke(main, ["run", "list"])
    assert result.exit_code == 0
    assert "No executions" in result.output


def test_list_human_pagination_hint(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(list_executions=_list_items(), total=47),
    ):
        result = runner.invoke(main, ["run", "list"])
    assert result.exit_code == 0
    assert "Showing 2 of 47" in result.output


# ── JSON mode ───────────────────────────────────────────────────────────


def test_list_json(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(list_executions=_list_items(), total=2),
    ):
        result = runner.invoke(main, ["--output", "json", "run", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, dict)
    assert "items" in parsed
    assert "total" in parsed
    assert "limit" in parsed
    assert "offset" in parsed
    assert len(parsed["items"]) == 2
    assert parsed["items"][0]["status"] == "COMPLETED"
    assert parsed["items"][1]["status"] == "RUNNING"
    assert parsed["total"] == 2


def test_list_json_empty(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(list_executions=[]),
    ):
        result = runner.invoke(main, ["--output", "json", "run", "list"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == {"items": [], "total": 0, "limit": 20, "offset": 0}


# ── quiet mode ──────────────────────────────────────────────────────────


def test_list_quiet(runner: CliRunner) -> None:
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client(list_executions=_list_items()),
    ):
        result = runner.invoke(main, ["--quiet", "run", "list"])
    assert result.exit_code == 0
    assert result.output == ""


# ── filter options ──────────────────────────────────────────────────────


def test_list_passes_filters(runner: CliRunner) -> None:
    mock = _mock_client(list_executions=[])
    with patch("cli.commands.run.AtlasClient", return_value=mock):
        runner.invoke(
            main,
            [
                "run", "list",
                "--benchmark-version-id", BENCH_VERSION_ID,
                "--status", "RUNNING",
                "--limit", "5",
                "--offset", "10",
            ],
        )
    mock.list_executions.assert_called_once_with(
        benchmark_version_id=BENCH_VERSION_ID,
        status="RUNNING",
        limit=5,
        offset=10,
    )


# ── auth error ──────────────────────────────────────────────────────────


def test_list_no_token(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="list"),
    ):
        result = runner.invoke(main, ["run", "list"])
    assert result.exit_code == 3


def test_list_no_token_json(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Not authenticated")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="list"),
    ):
        result = runner.invoke(
            main, ["--output", "json", "run", "list"]
        )
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert "error" in parsed


# ── not found ───────────────────────────────────────────────────────────


def test_list_not_found(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="Not found")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="list"),
    ):
        result = runner.invoke(main, ["run", "list"])
    assert result.exit_code == 5


# ── network error ───────────────────────────────────────────────────────


def test_list_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    err = NetworkError(message="connection refused")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="list"),
    ):
        result = runner.invoke(main, ["run", "list"])
    assert result.exit_code == 6


# ── server error ────────────────────────────────────────────────────────


def test_list_server_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ServerError

    err = ServerError(status=500, message="Internal server error")
    with patch(
        "cli.commands.run.AtlasClient",
        return_value=_mock_client_error(err, method="list"),
    ):
        result = runner.invoke(main, ["run", "list"])
    assert result.exit_code == 1


# =====================================================================
# atlas run watch
# =====================================================================


EXEC_ID_WATCH = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _exec_response_for(status: str) -> ExecutionResponse:
    """Build an ExecutionResponse for a given status."""
    return ExecutionResponse(
        id=uuid.UUID(EXEC_ID_WATCH),
        benchmark_version_id=uuid.UUID(BENCH_VERSION_ID),
        status=status,
        target_model="gemini-2.5-flash",
        completed_items=7 if status == "COMPLETED" else 3,
        total_items=10,
        started_at=datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC),
        completed_at=(
            datetime(2026, 8, 26, 12, 5, 0, tzinfo=UTC)
            if status in ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT")
            else None
        ),
        created_at=datetime(2026, 8, 26, 11, 55, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 26, 12, 5, 0, tzinfo=UTC),
        created_by=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        max_retries=3,
        attempts=[],
    )


def _mock_watch_client(
    get_execution_side_effect: list | Exception | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    if get_execution_side_effect is not None:
        mock.get_execution.side_effect = get_execution_side_effect
    return mock


# ── discovery ───────────────────────────────────────────────────────────


def test_run_watch_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    assert "watch" in result.output.lower()


# ── already terminal ────────────────────────────────────────────────────


def test_watch_already_terminal(runner: CliRunner) -> None:
    """Execution is already terminal — exits immediately."""
    mock = _mock_watch_client(
        get_execution_side_effect=[_exec_response_for("COMPLETED")],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep") as mock_sleep,
    ):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 0
    assert "COMPLETED" in result.output
    mock_sleep.assert_not_called()


# ── terminal state variants ─────────────────────────────────────────────


def test_watch_failed_terminal(runner: CliRunner) -> None:
    mock = _mock_watch_client(
        get_execution_side_effect=[_exec_response_for("FAILED")],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 0
    assert "FAILED" in result.output


def test_watch_cancelled_terminal(runner: CliRunner) -> None:
    mock = _mock_watch_client(
        get_execution_side_effect=[_exec_response_for("CANCELLED")],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 0
    assert "CANCELLED" in result.output


def test_watch_timed_out_terminal(runner: CliRunner) -> None:
    mock = _mock_watch_client(
        get_execution_side_effect=[_exec_response_for("TIMED_OUT")],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 0
    assert "TIMED_OUT" in result.output


# ── poll through to completion ──────────────────────────────────────────


def test_watch_polls_to_completed(runner: CliRunner) -> None:
    """Queued → Running → Completed."""
    mock = _mock_watch_client(
        get_execution_side_effect=[
            _exec_response_for("QUEUED"),
            _exec_response_for("RUNNING"),
            _exec_response_for("COMPLETED"),
        ],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep") as mock_sleep,
    ):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 0
    assert "COMPLETED" in result.output
    assert mock_sleep.call_count == 2
    assert mock.get_execution.call_count == 3


# ── JSON output ─────────────────────────────────────────────────────────


def test_watch_json_final_state_only(runner: CliRunner) -> None:
    """JSON mode: no stdout during poll, one final JSON object."""
    mock = _mock_watch_client(
        get_execution_side_effect=[
            _exec_response_for("RUNNING"),
            _exec_response_for("COMPLETED"),
        ],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(
            main, ["--output", "json", "run", "watch", EXEC_ID_WATCH]
        )
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == EXEC_ID_WATCH
    assert parsed["status"] == "COMPLETED"


# ── quiet mode ──────────────────────────────────────────────────────────


def test_watch_quiet(runner: CliRunner) -> None:
    mock = _mock_watch_client(
        get_execution_side_effect=[_exec_response_for("COMPLETED")],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(
            main, ["--quiet", "run", "watch", EXEC_ID_WATCH]
        )
    assert result.exit_code == 0
    assert result.output == ""


# ── Ctrl+C → 130 ───────────────────────────────────────────────────────


def test_watch_keyboard_interrupt(runner: CliRunner) -> None:
    mock = _mock_watch_client(
        get_execution_side_effect=[
            _exec_response_for("RUNNING"),
            KeyboardInterrupt(),
        ],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 130


# ── transient network failure ───────────────────────────────────────────


def test_watch_transient_network_failure(runner: CliRunner) -> None:
    """One network failure followed by success."""
    from atlas_sdk.errors import NetworkError

    mock = _mock_watch_client(
        get_execution_side_effect=[
            NetworkError(message="connection refused"),
            _exec_response_for("COMPLETED"),
        ],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 0
    assert "COMPLETED" in result.output


# ── three consecutive network failures ──────────────────────────────────


def test_watch_consecutive_network_failures(runner: CliRunner) -> None:
    """3 consecutive network failures → exit 1."""
    from atlas_sdk.errors import NetworkError

    mock = _mock_watch_client(
        get_execution_side_effect=[
            NetworkError(message="fail 1"),
            NetworkError(message="fail 2"),
            NetworkError(message="fail 3"),
        ],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 1


def test_watch_consecutive_network_failures_json(runner: CliRunner) -> None:
    """3 failures in JSON mode → last-known state emitted."""
    from atlas_sdk.errors import NetworkError

    mock = _mock_watch_client(
        get_execution_side_effect=[
            _exec_response_for("RUNNING"),
            NetworkError(message="fail 1"),
            NetworkError(message="fail 2"),
            NetworkError(message="fail 3"),
        ],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep"),
    ):
        result = runner.invoke(
            main, ["--output", "json", "run", "watch", EXEC_ID_WATCH]
        )
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["status"] == "RUNNING"


# ── API errors (non-transient) ─────────────────────────────────────────


def test_watch_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    err = AuthError(status=401, message="Unauthorized")
    mock = _mock_watch_client(get_execution_side_effect=err)
    with patch("cli.commands.run.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 3


def test_watch_403(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    err = ForbiddenError(status=403, message="Forbidden")
    mock = _mock_watch_client(get_execution_side_effect=err)
    with patch("cli.commands.run.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 4


def test_watch_404(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    err = NotFoundError(status=404, message="Not found")
    mock = _mock_watch_client(get_execution_side_effect=err)
    with patch("cli.commands.run.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH])
    assert result.exit_code == 5


# ── polling interval ────────────────────────────────────────────────────


def test_watch_custom_interval(runner: CliRunner) -> None:
    """Verify custom interval is passed through."""
    mock = _mock_watch_client(
        get_execution_side_effect=[_exec_response_for("COMPLETED")],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep") as mock_sleep,
    ):
        result = runner.invoke(
            main, ["run", "watch", EXEC_ID_WATCH, "--interval", "5"]
        )
    assert result.exit_code == 0
    mock_sleep.assert_not_called()  # already terminal


def test_watch_interval_used_between_polls(runner: CliRunner) -> None:
    """Verify sleep is called with the interval between non-terminal polls."""
    mock = _mock_watch_client(
        get_execution_side_effect=[
            _exec_response_for("RUNNING"),
            _exec_response_for("COMPLETED"),
        ],
    )
    with (
        patch("cli.commands.run.AtlasClient", return_value=mock),
        patch("cli.commands.run.time.sleep") as mock_sleep,
    ):
        result = runner.invoke(
            main, ["run", "watch", EXEC_ID_WATCH, "--interval", "7"]
        )
    assert result.exit_code == 0
    mock_sleep.assert_called_once_with(7)


# ── invalid interval ────────────────────────────────────────────────────


def test_watch_invalid_interval_zero(runner: CliRunner) -> None:
    """--interval 0 is rejected."""
    result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH, "--interval", "0"])
    assert result.exit_code != 0
    assert "greater than 0" in result.output


def test_watch_invalid_interval_negative(runner: CliRunner) -> None:
    """--interval -3 is rejected."""
    result = runner.invoke(main, ["run", "watch", EXEC_ID_WATCH, "--interval", "-3"])
    assert result.exit_code != 0
    assert "greater than 0" in result.output
