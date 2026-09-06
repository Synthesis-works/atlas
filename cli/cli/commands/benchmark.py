"""benchmark commands — list, get, versions (Phase 1).

Implements:
  atlas benchmark list          (human-readable table)
  atlas benchmark list --json   (JSON output)
  atlas benchmark list --quiet  (exit code only)
  atlas benchmark get <id>      (human-readable detail)
  atlas benchmark get <id> --json   (JSON output)
  atlas benchmark get <id> --quiet  (exit code only)
  atlas benchmark versions <id>     (human-readable table)
  atlas benchmark versions <id> --json  (JSON output)
  atlas benchmark versions <id> --quiet (exit code only)
"""

from __future__ import annotations

import click
from atlas_sdk import BenchmarkRead, PageResponse

from cli.app import Context, _pass_context
from cli.client import build_client
from cli.config import AtlasConfig
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.schema import emit_json_schema
from cli.output.table import render_kv, render_table


@click.group(name="benchmark")
def benchmark_group() -> None:
    """Benchmark operations.

    Examples:

      atlas benchmark list

      atlas benchmark get <benchmark-id>

      atlas benchmark versions <benchmark-id>
    """


@benchmark_group.command(name="list")
@click.option(
    "--json-schema",
    is_flag=True,
    default=False,
    help="Print the JSON Schema of this command's JSON output (offline) and exit.",
)
@_pass_context
def list_cmd(ctx: Context, json_schema: bool) -> None:
    """List published benchmarks.

    Calls GET /api/v1/benchmarks through the SDK.

    Examples:

      atlas benchmark list

      atlas benchmark list --output json

      atlas benchmark list --json-schema
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    if json_schema:
        emit_json_schema(PageResponse[BenchmarkRead], output_mode=output_mode)
        return

    try:
        with build_client(cfg) as client:
            page = client.list_benchmarks(limit=50)
    except Exception as exc:
        error_exit(exc, output_mode)

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
        rows = [[b.name, str(b.id), b.state] for b in page.items]
        render_table(headers, rows, title="Benchmarks")
        if page.total > len(page.items):
            shown = len(page.items)
            click.echo(f"  Showing {shown} of {page.total}")


@benchmark_group.command(name="get")
@click.option(
    "--json-schema",
    is_flag=True,
    default=False,
    help="Print the JSON Schema of this command's JSON output (offline) and exit.",
)
@_pass_context
@click.argument("benchmark_id")
def get_cmd(ctx: Context, benchmark_id: str, json_schema: bool) -> None:
    """Show details for a single benchmark.

    Calls GET /api/v1/benchmarks/{id} through the SDK.

    Examples:

      atlas benchmark get <benchmark-id>

      atlas benchmark get <benchmark-id> --json-schema
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    if json_schema:
        emit_json_schema(BenchmarkRead, output_mode=output_mode)
        return

    try:
        with build_client(cfg) as client:
            benchmark = client.get_benchmark(benchmark_id)
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        render_json(benchmark.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        rows: list[tuple[str, str]] = [
            ("Name", benchmark.name),
            ("ID", str(benchmark.id)),
            ("Project ID", str(benchmark.project_id)),
            ("State", benchmark.state),
        ]
        render_kv(rows, title="Benchmark")


@benchmark_group.command(name="versions")
@_pass_context
@click.argument("benchmark_id")
def versions_cmd(ctx: Context, benchmark_id: str) -> None:
    """List versions for a benchmark.

    Calls GET /api/v1/benchmarks/{id}/versions through the SDK.

    Examples:

      atlas benchmark versions <benchmark-id>
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
            versions = client.list_benchmark_versions(benchmark_id)
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        items = [v.model_dump(mode="json") for v in versions]
        render_json({"items": items, "total": len(items)})
    elif output_mode == "quiet":
        pass
    else:
        if not versions:
            click.echo("  (no versions)")
            return
        headers = ["Version", "ID", "State"]
        rows = [[v.version_string, str(v.id), v.state] for v in versions]
        render_table(headers, rows, title="Benchmark Versions")
