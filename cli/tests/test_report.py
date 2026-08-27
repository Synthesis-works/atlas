"""Tests for `atlas report list`.

Mocks at the SDK boundary to test CLI rendering without real HTTP.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from atlas_sdk.models.reports import PaginatedReportRunsRead, ReportRunEntryRead
from click.testing import CliRunner

from cli.app import main


def _report_entry(
    *,
    run_id: str = "11111111-1111-1111-1111-111111111111",
    target_model: str = "gpt-4o",
    benchmark_version: str = "1.0.0",
    evaluation_status: str = "COMPLETED",
    overall_score: float | None = 88.5,
) -> ReportRunEntryRead:
    return ReportRunEntryRead(
        run_id=uuid.UUID(run_id),
        benchmark_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        benchmark_version=benchmark_version,
        target_model=target_model,
        evaluation_status=evaluation_status,
        started_at=datetime(2026, 8, 26, 10, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 8, 26, 10, 5, 0, tzinfo=UTC),
        overall_score=overall_score,
    )


def _mock_page(
    items: list[ReportRunEntryRead] | None = None,
    total: int = 2,
    page: int = 1,
    size: int = 50,
) -> PaginatedReportRunsRead:
    if items is None:
        items = [
            _report_entry(target_model="gpt-4o", overall_score=88.5),
            _report_entry(
                run_id="33333333-3333-3333-3333-333333333333",
                target_model="claude-3",
                evaluation_status="RUNNING",
                overall_score=None,
            ),
        ]
    return PaginatedReportRunsRead(items=items, total=total, page=page, size=size)


def _mock_client(
    page: PaginatedReportRunsRead | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_report_runs.return_value = page or _mock_page()
    return mock


def _mock_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_report_runs.side_effect = exc
    return mock


# ── discovery ───────────────────────────────────────────────────────────


def test_report_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "report" in result.output.lower()


def test_report_list_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["report", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output.lower()


def test_report_list_subcommand_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["report", "list", "--help"])
    assert result.exit_code == 0
    assert "status" in result.output.lower()


# ── human mode ──────────────────────────────────────────────────────────


def test_report_list_human(runner: CliRunner) -> None:
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 0
    assert "11111111" in result.output
    assert "gpt-4o" in result.output
    assert "claude-3" in result.output
    assert "COMPLETED" in result.output
    assert "RUNNING" in result.output
    assert "88.5" in result.output
    assert "Report Runs" in result.output


def test_report_list_human_with_none_score(runner: CliRunner) -> None:
    entry = _report_entry(overall_score=None, evaluation_status="RUNNING")
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(page=_mock_page(items=[entry], total=1)),
    ):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 0
    assert "-" in result.output


def test_report_list_human_empty(runner: CliRunner) -> None:
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(page=_mock_page(items=[], total=0)),
    ):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 0
    assert "(no reports)" in result.output


def test_report_list_human_pagination_hint(runner: CliRunner) -> None:
    entry = _report_entry()
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(page=_mock_page(items=[entry], total=50)),
    ):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 0
    assert "Showing 1 of 50" in result.output


# ── json mode ───────────────────────────────────────────────────────────


def test_report_list_json(runner: CliRunner) -> None:
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(main, ["--output", "json", "report", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert len(data["items"]) == 2
    assert data["total"] == 2


def test_report_list_json_empty(runner: CliRunner) -> None:
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(page=_mock_page(items=[], total=0)),
    ):
        result = runner.invoke(main, ["--output", "json", "report", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["items"] == []
    assert data["total"] == 0


def test_report_list_json_preserves_page_size(runner: CliRunner) -> None:
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(page=_mock_page(total=100, page=2, size=25)),
    ):
        result = runner.invoke(main, ["--output", "json", "report", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["page"] == 2
    assert data["size"] == 25
    assert data["total"] == 100


# ── quiet mode ──────────────────────────────────────────────────────────


def test_report_list_quiet(runner: CliRunner) -> None:
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(main, ["--quiet", "report", "list"])
    assert result.exit_code == 0
    assert result.output == ""


def test_report_list_quiet_via_shorthand(runner: CliRunner) -> None:
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(),
    ):
        result = runner.invoke(main, ["-q", "report", "list"])
    assert result.exit_code == 0
    assert result.output == ""


# ── filters ─────────────────────────────────────────────────────────────


def test_report_list_filter_status(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        runner.invoke(main, ["report", "list", "--status", "COMPLETED"])
    mock.list_report_runs.assert_called_once_with(
        status="COMPLETED",
        benchmark_id=None,
        benchmark_version=None,
        target_model=None,
        limit=50,
        offset=0,
    )


def test_report_list_filter_benchmark_id(runner: CliRunner) -> None:
    bid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    mock = _mock_client()
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        runner.invoke(main, ["report", "list", "--benchmark-id", bid])
    mock.list_report_runs.assert_called_once_with(
        status=None,
        benchmark_id=bid,
        benchmark_version=None,
        target_model=None,
        limit=50,
        offset=0,
    )


def test_report_list_filter_benchmark_version(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        runner.invoke(main, ["report", "list", "--benchmark-version", "2.0.0"])
    mock.list_report_runs.assert_called_once_with(
        status=None,
        benchmark_id=None,
        benchmark_version="2.0.0",
        target_model=None,
        limit=50,
        offset=0,
    )


def test_report_list_filter_target_model(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        runner.invoke(main, ["report", "list", "--target-model", "gpt-4o"])
    mock.list_report_runs.assert_called_once_with(
        status=None,
        benchmark_id=None,
        benchmark_version=None,
        target_model="gpt-4o",
        limit=50,
        offset=0,
    )


def test_report_list_all_filters(runner: CliRunner) -> None:
    bid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    mock = _mock_client()
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        runner.invoke(main, [
            "report", "list",
            "--status", "FAILED",
            "--benchmark-id", bid,
            "--benchmark-version", "3.0.0",
            "--target-model", "claude-3",
            "--limit", "10",
            "--offset", "5",
        ])
    mock.list_report_runs.assert_called_once_with(
        status="FAILED",
        benchmark_id=bid,
        benchmark_version="3.0.0",
        target_model="claude-3",
        limit=10,
        offset=5,
    )


def test_report_list_pagination_params(runner: CliRunner) -> None:
    mock = _mock_client()
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        runner.invoke(main, ["report", "list", "--limit", "10", "--offset", "20"])
    mock.list_report_runs.assert_called_once_with(
        status=None,
        benchmark_id=None,
        benchmark_version=None,
        target_model=None,
        limit=10,
        offset=20,
    )


# ── errors ──────────────────────────────────────────────────────────────


def test_report_list_401(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Unauthorized"))
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 3


def test_report_list_403(runner: CliRunner) -> None:
    from atlas_sdk.errors import ForbiddenError

    mock = _mock_client_error(ForbiddenError(status=403, message="Forbidden"))
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 4


def test_report_list_404(runner: CliRunner) -> None:
    from atlas_sdk.errors import NotFoundError

    mock = _mock_client_error(NotFoundError(status=404, message="Not found"))
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 5


def test_report_list_network_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import NetworkError

    mock = _mock_client_error(NetworkError(message="Connection refused"))
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 6


def test_report_list_server_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import ServerError

    mock = _mock_client_error(ServerError(status=500, message="Internal error"))
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 1


def test_report_list_json_error(runner: CliRunner) -> None:
    from atlas_sdk.errors import AuthError

    mock = _mock_client_error(AuthError(status=401, message="Expired token"))
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["--output", "json", "report", "list"])
    assert result.exit_code == 3


def test_report_list_unexpected_error(runner: CliRunner) -> None:
    mock = _mock_client_error(RuntimeError("something broke"))
    with patch("cli.commands.report.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 1


# ── dto parsing ─────────────────────────────────────────────────────────


def test_report_list_dto_fields(runner: CliRunner) -> None:
    entry = ReportRunEntryRead(
        run_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        benchmark_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        benchmark_version="4.0.0",
        target_model="gemini-2.5-flash",
        evaluation_status="COMPLETED",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 2, tzinfo=UTC),
        overall_score=95.0,
    )
    page = PaginatedReportRunsRead(items=[entry], total=1, page=1, size=50)
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(page=page),
    ):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 0
    assert "aaaaaaaa" in result.output
    assert "gemini-2.5-flash" in result.output
    assert "4.0.0" in result.output
    assert "95.0" in result.output
    assert "2026-01-02" in result.output


def test_report_list_dto_with_null_fields(runner: CliRunner) -> None:
    entry = ReportRunEntryRead(
        run_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        benchmark_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        benchmark_version="1.0.0",
        target_model="test-model",
        evaluation_status="PENDING",
        started_at=None,
        completed_at=None,
        overall_score=None,
    )
    page = PaginatedReportRunsRead(items=[entry], total=1, page=1, size=50)
    with patch(
        "cli.commands.report.AtlasClient",
        return_value=_mock_client(page=page),
    ):
        result = runner.invoke(main, ["report", "list"])
    assert result.exit_code == 0
    assert "-" in result.output
