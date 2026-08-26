"""Shared CLI error rendering and exit (§10).

All commands use the same pattern for rendering SDK errors and exiting
with the appropriate code.  This module provides that shared behavior.
"""

from __future__ import annotations

import sys

from cli.errors import exit_code_for_error
from cli.output.json import render_json_error


def error_exit(exc: Exception, output_mode: str) -> None:
    """Render an SDK error and exit with the appropriate code.

    In JSON mode, writes a structured error document to stderr.
    In human mode, writes a plain-text error to stderr.
    Then exits with the mapped exit code.
    """
    if output_mode == "json":
        render_json_error(
            status=getattr(exc, "status", 0),
            code=getattr(exc, "code", "UNKNOWN"),
            message=str(exc),
            details=getattr(exc, "details", None),
        )
    else:
        import click

        click.echo(f"error: {exc}", err=True)
    sys.exit(exit_code_for_error(exc))
