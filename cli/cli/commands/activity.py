"""activity command.

Implements:
  atlas activity
  atlas activity --type benchmarks|executions|models
  atlas activity --limit 20
  atlas activity --output json
  atlas activity --quiet

Calls GET /api/v1/history/{benchmarks,executions,models}/recent.
"""

from __future__ import annotations

from datetime import datetime

import click
from atlas_sdk import BenchmarkRead, ExecutionHistoryRead, ModelActivityRead

from cli.app import Context, _pass_context
from cli.client import build_client
from cli.config import AtlasConfig
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.table import render_table

_TYPE_CHOICES = ("benchmarks", "executions", "models")


@click.command(name="activity")
@_pass_context
@click.option(
    "--type",
    "activity_type",
    type=click.Choice(_TYPE_CHOICES),
    default=None,
    help="Restrict to one activity kind (benchmarks, executions, models).",
)
@click.option(
    "--limit",
    default=10,
    type=int,
    show_default=True,
    help="Maximum number of entries per section (default: 10).",
)
def activity_cmd(
    ctx: Context,
    activity_type: str | None,
    limit: int,
) -> None:
    """Show recent platform activity.

    By default shows the most recent published benchmarks, executions,
    and active models.  Use --type to show a single section, and
    --limit to control how many entries each section lists.

    Examples:

      atlas activity

      atlas activity --type executions --limit 5

      atlas activity --output json
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
            kwargs = {"limit": limit}
            if activity_type in (None, "benchmarks"):
                benchmarks = client.get_recent_benchmarks(**kwargs)
            else:
                benchmarks = None
            if activity_type in (None, "executions"):
                executions = client.get_recent_executions(**kwargs)
            else:
                executions = None
            if activity_type in (None, "models"):
                models = client.get_recent_models(**kwargs)
            else:
                models = None
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        payload: dict[str, object] = {}
        if benchmarks is not None:
            payload["benchmarks"] = [b.model_dump(mode="json") for b in benchmarks]
        if executions is not None:
            payload["executions"] = [e.model_dump(mode="json") for e in executions]
        if models is not None:
            payload["models"] = [m.model_dump(mode="json") for m in models]
        render_json(payload)
    elif output_mode == "quiet":
        pass
    else:
        _render_human(benchmarks, executions, models)


def _render_human(
    benchmarks: list[BenchmarkRead] | None,
    executions: list[ExecutionHistoryRead] | None,
    models: list[ModelActivityRead] | None,
) -> None:
    """Render recent activity in human-readable form."""
    click.echo("Recent Activity")

    if benchmarks is not None:
        if benchmarks:
            rows_data = [
                [b.name, b.state, str(b.id)[:8]]
                for b in benchmarks
            ]
            render_table(
                ["Benchmark", "State", "ID"],
                rows_data,
                title=f"Benchmarks ({len(benchmarks)})",
            )
        else:
            click.echo("  (no recent benchmarks)")

    if executions is not None:
        if executions:
            rows_data = [
                [e.target_model, e.benchmark_name, e.status.value, _fmt_ts(e.started_at)]
                for e in executions
            ]
            render_table(
                ["Model", "Benchmark", "Status", "Started"],
                rows_data,
                title=f"Executions ({len(executions)})",
            )
        else:
            click.echo("  (no recent executions)")

    if models is not None:
        if models:
            rows_data = [
                [m.name, _fmt_ts(m.last_executed_at), str(m.execution_count)]
                for m in models
            ]
            render_table(
                ["Model", "Last Executed", "Runs"],
                rows_data,
                title=f"Models ({len(models)})",
            )
        else:
            click.echo("  (no recent models)")


def _fmt_ts(timestamp: datetime | None) -> str:
    """Format a datetime for display, tolerating ``None``."""
    if timestamp is None:
        return "-"
    return timestamp.strftime("%Y-%m-%d %H:%M")
