"""Tests for the output contract — stdout purity in JSON mode (§9.2)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cli.app import main


def test_json_mode_stdout_is_pure_json(runner: CliRunner) -> None:
    """JSON mode: stdout must contain exactly one JSON document, nothing else."""
    result = runner.invoke(main, ["--output", "json", "whoami"])
    parsed = json.loads(result.output)
    assert isinstance(parsed, dict)


def test_health_json_stdout_is_pure_json(runner: CliRunner) -> None:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.health_summary.side_effect = Exception("no server")
    mock.system_live.side_effect = Exception("no server")
    mock.system_ready.side_effect = Exception("no server")
    with patch("cli.commands.health.AtlasClient", return_value=mock):
        result = runner.invoke(main, ["--output", "json", "health"])
    parsed = json.loads(result.output)
    assert isinstance(parsed, dict)
    assert "overall" in parsed


def test_errors_go_to_stdout_as_json(runner: CliRunner) -> None:
    """When whoami fails (no token), error is emitted as JSON."""
    result = runner.invoke(main, ["--output", "json", "whoami"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert "error" in parsed
    assert parsed["error"]["status"] == 401
