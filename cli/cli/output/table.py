"""Human-readable table renderer — aligned text output for tty usage."""

from __future__ import annotations

import sys
from typing import Any


def render_kv(rows: list[tuple[str, str]], *, title: str = "", file: Any | None = None) -> None:
    """Render key-value pairs as a readable block.

    Args:
        rows: list of (label, value) pairs.
        title: optional heading (printed above the block).
        file: output target (defaults to stdout).
    """
    target = file or sys.stdout
    if title:
        target.write(f"\033[1m{title}\033[0m\n\n" if _is_tty(target) else f"{title}\n\n")

    if not rows:
        target.write("  (no data)\n")
        return

    max_label = max(len(label) for label, _ in rows)
    for label, value in rows:
        padded = label.rjust(max_label)
        target.write(f"  {padded}:  {value}\n")


def render_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    title: str = "",
    file: Any | None = None,
) -> None:
    """Render a simple aligned table.

    Args:
        headers: column headers.
        rows: list of row-data lists, each row matching headers length.
        title: optional heading.
        file: output target (defaults to stdout).
    """
    target = file or sys.stdout
    if title:
        target.write(f"\033[1m{title}\033[0m\n\n" if _is_tty(target) else f"{title}\n\n")

    if not rows:
        target.write("  (empty)\n")
        return

    # Compute column widths.
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    # Header.
    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    target.write(f"  {header_line}\n")

    # Separator.
    sep = "  ".join("-" * w for w in col_widths)
    target.write(f"  {sep}\n")

    # Rows.
    for row in rows:
        line = "  ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))
        target.write(f"  {line}\n")


def render_message(message: str, *, file: Any | None = None) -> None:
    """Write a simple informational message to stdout."""
    target = file or sys.stdout
    target.write(f"{message}\n")


def render_warning(message: str) -> None:
    """Write a warning to stderr."""
    sys.stderr.write(f"warning: {message}\n")


def _is_tty(file: Any) -> bool:
    try:
        return hasattr(file, "isatty") and file.isatty()
    except Exception:
        return False
