"""Golden-file tests — establish the snapshot mechanism (§13).

These tests record expected JSON output shapes and guard against
inadvertent schema drift.  When a golden file changes, the diff
must be reviewed as a potential contract break.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from atlas_sdk.errors import NetworkError
from click.testing import CliRunner

from cli.app import main

GOLDEN_DIR = Path(__file__).parent / "golden"


def _load_golden(name: str) -> dict | list:
    path = GOLDEN_DIR / name
    if not path.exists():
        pytest.skip(f"golden file {name} not yet created")
    return json.loads(path.read_text())


def _write_golden(name: str, data: dict | list) -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    (GOLDEN_DIR / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _mock_all_fail():
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.health_summary.side_effect = NetworkError(message="no server")
    mock.system_live.side_effect = NetworkError(message="no server")
    mock.system_ready.side_effect = NetworkError(message="no server")
    return mock


def test_whoami_error_json_matches_golden(runner: CliRunner) -> None:
    """Record the expected shape of `atlas whoami --output json` on auth error."""
    result = runner.invoke(main, ["--output", "json", "whoami"])
    assert result.exit_code == 3
    parsed = json.loads(result.output)

    golden_name = "whoami_error.json"
    existing = _load_golden(golden_name) if (GOLDEN_DIR / golden_name).exists() else None
    if existing is None:
        _write_golden(golden_name, parsed)
        pytest.skip(f"created golden file {golden_name}")
    assert parsed == existing, f"golden mismatch for {golden_name}"


def test_health_degraded_json_matches_golden(runner: CliRunner) -> None:
    """Record the expected shape of `atlas health --output json` when degraded."""
    with patch("cli.client.AtlasClient", return_value=_mock_all_fail()):
        result = runner.invoke(main, ["--output", "json", "health"])
    assert result.exit_code == 1
    parsed = json.loads(result.output)

    golden_name = "health_degraded.json"
    existing = _load_golden(golden_name) if (GOLDEN_DIR / golden_name).exists() else None
    if existing is None:
        _write_golden(golden_name, parsed)
        pytest.skip(f"created golden file {golden_name}")
    assert set(parsed.keys()) == set(existing.keys()), f"golden key mismatch for {golden_name}"
    assert parsed["overall"] == existing["overall"]
