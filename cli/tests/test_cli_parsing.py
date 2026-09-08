"""Tests for CLI parsing — --help, --version, global options, command discovery."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cli import __version__
from cli.app import entrypoint, main


def test_help_exits_zero(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Atlas CLI" in result.output


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_subcommand_shows_help(runner: CliRunner) -> None:
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "Atlas CLI" in result.output


def test_unknown_command_returns_error(runner: CliRunner) -> None:
    result = runner.invoke(main, ["nonexistent"])
    assert result.exit_code != 0


def test_whoami_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert "whoami" in result.output


def test_health_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert "health" in result.output


def test_output_flag_invalid(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--output", "invalid"])
    assert result.exit_code != 0


def test_retries_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--retries" in result.output


def test_entrypoint_negative_retries_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["atlas", "--retries", "-1", "health"])
    with pytest.raises(SystemExit) as exc_info:
        entrypoint()
    assert exc_info.value.code == 2
    captured = capsys.readouterr().err
    assert "retries" in captured
    assert "Traceback" not in captured


def test_entrypoint_noninteger_retries_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["atlas", "--retries", "many", "health"])
    with pytest.raises(SystemExit) as exc_info:
        entrypoint()
    assert exc_info.value.code == 2
    assert "Traceback" not in capsys.readouterr().err


def test_entrypoint_negative_retries_env_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["atlas", "health"])
    monkeypatch.setenv("ATLAS_RETRIES", "-2")
    with pytest.raises(SystemExit) as exc_info:
        entrypoint()
    assert exc_info.value.code == 2
    assert "retries" in capsys.readouterr().err


# ── entrypoint (console script) behavior ─────────────────────────────────
#
# Tests invoke ``main`` via CliRunner, which swallows click exceptions and
# reports exit code 2.  The real ``atlas`` executable runs ``entrypoint``
# with standalone_mode=False, so it must translate click usage errors
# itself (clean stderr message, exit 2, no traceback).


def test_entrypoint_unknown_command_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["atlas", "nonexistent"])
    with pytest.raises(SystemExit) as exc_info:
        entrypoint()
    assert exc_info.value.code == 2
    assert "Error:" in capsys.readouterr().err


def test_entrypoint_invalid_choice_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["atlas", "activity", "--type", "bogus"])
    with pytest.raises(SystemExit) as exc_info:
        entrypoint()
    assert exc_info.value.code == 2
    captured = capsys.readouterr().err
    assert "bogus" in captured
    assert "Traceback" not in captured


def test_entrypoint_mutually_exclusive_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["atlas", "leaderboard", "model", "mock", "--history", "--benchmarks"],
    )
    with pytest.raises(SystemExit) as exc_info:
        entrypoint()
    assert exc_info.value.code == 2
    assert "mutually exclusive" in capsys.readouterr().err


def test_entrypoint_watch_timeout_zero_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "atlas",
            "run",
            "watch",
            "11111111-1111-1111-1111-111111111111",
            "--timeout",
            "0",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        entrypoint()
    assert exc_info.value.code == 2
    captured = capsys.readouterr().err
    assert "greater than 0" in captured
    assert "Traceback" not in captured
