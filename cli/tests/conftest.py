"""conftest.py — shared fixtures for CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _isolate_cli_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test isolated from the real user config directory.

    The test's ``tmp_path`` doubles as ``APPDATA`` so commands persist to a
    predictable ``tmp_path/Atlas/config.toml`` and never touch the real
    ``%APPDATA%\\Atlas\\config.toml``.
    """
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("ATLAS_TOKEN", raising=False)
