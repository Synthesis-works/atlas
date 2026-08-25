"""auth commands — whoami (Phase 1).

Implements:
  atlas whoami          (human-readable output)
  atlas whoami --json   (JSON output)
  atlas whoami --quiet  (no output, exit code only)
"""

from __future__ import annotations

import sys

import click
from atlas_sdk import AtlasClient, StaticTokenSupplier

from cli.app import Context, _pass_context
from cli.config import AtlasConfig
from cli.errors import ExitCode, exit_code_for_error
from cli.output.json import render_json, render_json_error
from cli.output.table import render_kv


@click.command(name="whoami")
@_pass_context
def whoami_cmd(ctx: Context) -> None:
    """Show the currently authenticated user.

    Calls GET /api/v1/auth/me through the SDK.
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    if not cfg.token:
        msg = "Not authenticated — run `atlas login` or set ATLAS_TOKEN."
        if output_mode == "json":
            render_json_error(status=401, code="UNAUTHORIZED", message=msg)
        else:
            click.echo(f"error: {msg}", err=True)
        sys.exit(ExitCode.AUTH_REQUIRED)

    try:
        supplier = StaticTokenSupplier(cfg.token)
        with AtlasClient(cfg.base_url, token_supplier=supplier, timeout=cfg.timeout) as client:
            user = client.whoami()
    except Exception as exc:
        if output_mode == "json":
            render_json_error(
                status=getattr(exc, "status", 0),
                code=getattr(exc, "code", "UNKNOWN"),
                message=str(exc),
                details=getattr(exc, "details", None),
            )
        else:
            click.echo(f"error: {exc}", err=True)
        sys.exit(exit_code_for_error(exc))

    if output_mode == "json":
        render_json(user.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        rows: list[tuple[str, str]] = [
            ("Email", user.email),
            ("Name", user.full_name),
            ("User ID", str(user.id)),
            ("Organization", str(user.org_id) if user.org_id else "(none)"),
            ("Active", "yes" if user.is_active else "no"),
            ("Verified", "yes" if user.is_verified else "no"),
        ]
        render_kv(rows, title="Atlas User")
