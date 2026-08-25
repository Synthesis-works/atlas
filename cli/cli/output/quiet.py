"""Quiet output renderer — no stdout output, meaningful exit codes only."""

from __future__ import annotations

from typing import Any


def render_quiet(data: Any, *, file: Any | None = None) -> None:
    """No-op: quiet mode emits nothing on stdout.  Exit codes carry meaning."""
