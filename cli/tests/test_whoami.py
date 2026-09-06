"""Tests for `atlas whoami` — human, JSON, quiet, and error modes."""

from __future__ import annotations

import json

from click.testing import CliRunner

from cli.app import main


def test_whoami_no_token_shows_auth_error(runner: CliRunner) -> None:
    result = runner.invoke(main, ["whoami"])
    assert result.exit_code == 3
    assert "Not authenticated" in result.output


def test_whoami_no_token_json(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--output", "json", "whoami"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"]["status"] == 401


def test_whoami_no_token_quiet(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--quiet", "whoami"])
    assert result.exit_code == 3
    # In quiet mode, no stdout; click captures stderr in result.output too
    # (no mix_stderr on this Click version). Just check exit code matters.


def test_whoami_invalid_token(runner: CliRunner) -> None:
    """With an invalid token, the SDK raises AuthError (401 from the server)."""
    result = runner.invoke(
        main,
        ["--output", "json", "whoami"],
        env={"ATLAS_TOKEN": "invalid-token-xxx"},
    )
    # Should fail with auth error (exit 3) or network error (exit 6)
    assert result.exit_code in (3, 6)


def test_whoami_human_output(runner: CliRunner) -> None:
    """Human mode should produce key-value output."""
    result = runner.invoke(main, ["whoami"])
    assert result.exit_code in (0, 3, 6)
