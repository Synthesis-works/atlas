"""``python -m cli`` module fallback (v0.1.3 Windows/PATH UX).

The installed console script may be on a ``Scripts`` directory that is not on
``PATH`` (common with MS Store / PythonCore installs).  ``python -m cli``
leverages the existing installed package; these tests prove the fallback
invokes the same CLI as the ``atlas`` entry point.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_SOURCE = Path(__file__).resolve().parents[1]  # cli/
_REPO = _SOURCE.parents[0]  # repo root (packages/, sdk/)


def _pythonpath() -> list[str]:
    existing = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    return [str(_SOURCE), str(_REPO / "sdk" / "python"), str(_REPO), *existing]


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(_pythonpath())
    env["APPDATA"] = str(cwd / "AppData")
    return subprocess.run(
        [sys.executable, "-m", "cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=120,
    )


def test_python_m_cli_version(tmp_path: Path) -> None:
    proc = _run("--version", cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "version" in proc.stdout


def test_python_m_cli_help(tmp_path: Path) -> None:
    proc = _run("--help", cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "Usage:" in proc.stdout
    assert "benchmark" in proc.stdout


def test_python_m_cli_unknown_command_routes_to_hosted_oneshot(tmp_path: Path) -> None:
    # Agent-first routing: a non-command first token is natural language, so a
    # typo'd command becomes a hosted one-shot request.  Without an Atlas
    # session that can't run: exit 10 with actionable guidance.
    proc = _run("definitely-not-a-command", cwd=tmp_path)
    assert proc.returncode == 10
    assert "atlas login" in proc.stderr


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
