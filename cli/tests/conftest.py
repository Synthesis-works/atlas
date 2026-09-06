"""conftest.py — shared fixtures for CLI tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

# ``packages.llm`` is a top-level ``packages`` package under the repo root.
# Make the repo root importable for the whole test session (mirrors how the
# backend gets ``packages`` on the path via PYTHONPATH) without touching the
# global site path, so the installed ``atlas`` executable is unaffected.
_TEST_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _TEST_ROOT.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


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
