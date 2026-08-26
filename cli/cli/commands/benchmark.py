"""benchmark commands — benchmark list (Phase 1).

Implements:
  atlas benchmark list          (human-readable table)
  atlas benchmark list --json   (JSON output)
  atlas benchmark list --quiet  (exit code only)
"""

from __future__ import annotations

import sys

import click
from atlas_sdk import AtlasClient, StaticTokenSupplier

from cli.app import Context, _pass_context
from cli.config import AtlasConfig
from cli.errors import exit_code_for_error
from cli.output.json import render_json, render_json_error
from cli.output.table import render_table


@click.group(name="benchmark")
def benchmark_group() -> None:
    """Benchmark operations."""


@benchmark_group.command(name="list")
@_pass_context
def list_cmd(ctx: Context) -> None:
    """List published benchmarks.

    Calls GET /api/v1/benchmarks through the SDK.
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    supplier = StaticTokenSupplier(cfg.token) if cfg.token else None

    try:
        with AtlasClient(
            cfg.base_url,
            token_supplier=supplier,
            timeout=cfg.timeout,
        ) as client:
            page = client.list_benchmarks(limit=50)
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
        result = {
            "items": [b.model_dump(mode="json") for b in page.items],
            "total": page.total,
            "limit": page.limit,
            "offset": page.offset,
            "next_cursor": page.next_cursor,
        }
        render_json(result)
    elif output_mode == "quiet":
        pass
    else:
        if not page.items:
            click.echo("  (no benchmarks)")
            return
        headers = ["Name", "ID", "State"]
        rows = [
            [b.name, str(b.id), b.state]
            for b in page.items
        ]
        render_table(headers, rows, title="Benchmarks")
        if page.total > len(page.items):
            shown = len(page.items)
            click.echo(f"  Showing {shown} of {page.total}")
