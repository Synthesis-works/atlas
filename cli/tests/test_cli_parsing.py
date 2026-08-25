"""Tests for CLI parsing — --help, --version, global options, command discovery."""

from __future__ import annotations

from click.testing import CliRunner

from cli.app import main


def test_help_exits_zero(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Atlas CLI" in result.output


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


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
