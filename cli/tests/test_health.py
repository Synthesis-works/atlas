"""Tests for `atlas health` — human, JSON, quiet, and degraded modes.

Mocks at the SDK boundary to test CLI rendering without real HTTP.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from atlas_sdk.errors import NetworkError
from click.testing import CliRunner

from cli.app import main


def _mock_client_all_fail():
    """Return a mock AtlasClient where all health methods raise."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.health_summary.side_effect = NetworkError(message="connection refused")
    mock.system_live.side_effect = NetworkError(message="connection refused")
    mock.system_ready.side_effect = NetworkError(message="connection refused")
    return mock


def test_health_degraded_all_down(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client_all_fail()):
        result = runner.invoke(main, ["health"])
    assert result.exit_code == 1
    assert "degraded" in result.output.lower()


def test_health_degraded_json_all_down(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client_all_fail()):
        result = runner.invoke(main, ["--output", "json", "health"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)
    assert parsed["overall"] == "degraded"
    assert parsed["api"] is None
    assert parsed["liveness"] is None
    assert parsed["readiness"] is None


def test_health_quiet_mode_degraded(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client_all_fail()):
        result = runner.invoke(main, ["--quiet", "health"])
    # Quiet mode: no stdout, exit 1 for degraded.
    assert result.output == ""
    assert result.exit_code == 1
