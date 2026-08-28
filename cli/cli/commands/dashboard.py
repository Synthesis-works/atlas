"""dashboard command.

Implements:
  atlas dashboard
  atlas dashboard --output json
  atlas dashboard --quiet

Calls GET /api/v1/dashboard through the SDK.
"""

from __future__ import annotations

import click
from atlas_sdk import AtlasClient, DashboardSnapshot, StaticTokenSupplier

from cli.app import Context, _pass_context
from cli.config import AtlasConfig
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.table import render_kv, render_table


@click.command(name="dashboard")
@_pass_context
def dashboard_cmd(ctx: Context) -> None:
    """Show the workspace dashboard summary.

    Displays run counters, platform resource counts, recent runs, and
    recent activity.
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
            snapshot = client.get_dashboard()
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        render_json(snapshot.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        _render_human(snapshot)


def _render_human(snapshot: DashboardSnapshot) -> None:
    """Render the dashboard snapshot in human-readable form."""
    summary = snapshot.summary
    hierarchy = snapshot.hierarchy

    click.echo("Atlas Dashboard")
    click.echo()

    run_rows: list[tuple[str, str]] = [
        ("Total", f"{summary.total_runs_count}"),
        ("Active", f"{summary.active_runs_count}"),
        ("Queued", f"{summary.queued_runs_count}"),
        ("Completed", f"{summary.completed_runs_count}"),
        ("Failed", f"{summary.failed_runs_count}"),
        ("Cancelled", f"{summary.cancelled_runs_count}"),
    ]
    render_kv(run_rows, title="Runs")

    platform_rows: list[tuple[str, str]] = [
        ("Benchmarks", f"{hierarchy.benchmarks}"),
        ("Datasets", f"{hierarchy.datasets}"),
        ("Evaluations", f"{hierarchy.evaluations}"),
        ("Models", f"{hierarchy.models}"),
        ("Reports", f"{hierarchy.reports}"),
    ]
    render_kv(platform_rows, title="Platform")

    jobs_rows: list[list[str]] = []
    seen: set[str] = set()
    for job in snapshot.recent_verified_runs + snapshot.active_executions:
        if job.id in seen:
            continue
        seen.add(job.id)
        jobs_rows.append([
            job.model,
            job.benchmark,
            job.status,
            f"{job.progress}%",
        ])
    if jobs_rows:
        render_table(
            ["Model", "Benchmark", "Status", "Progress"],
            jobs_rows[:8],
            title="Recent Runs",
        )

    activity = snapshot.activity
    if activity:
        click.echo("Recent Activity")
        for item in activity[:5]:
            when = _short_ts(item.timestamp)
            click.echo(f"  {when}  {item.title}")
    else:
        click.echo("  (no recent activity)")


def _short_ts(timestamp: str | None) -> str:
    """Collapse an ISO-8601 string to ``YYYY-MM-DD HH:MM`` when possible."""
    if not timestamp:
        return "?"
    value = timestamp[:16]
    return value.replace("T", " ")
