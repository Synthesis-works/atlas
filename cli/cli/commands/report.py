"""report commands -- list (Phase 1).

Implements:
  atlas report list
  atlas report list --output json
  atlas report list --quiet
"""

from __future__ import annotations

import click
from atlas_sdk import AtlasClient, StaticTokenSupplier

from cli.app import Context, _pass_context
from cli.config import AtlasConfig
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.table import render_table


@click.group(name="report")
def report_group() -> None:
    """Report operations."""


@report_group.command(name="list")
@_pass_context
@click.option(
    "--status",
    default=None,
    type=click.Choice(
        ["PENDING", "RUNNING", "EVALUATING", "COMPLETED", "PARTIAL_SUCCESS", "FAILED", "CANCELLED"],
        case_sensitive=False,
    ),
    help="Filter by evaluation status.",
)
@click.option(
    "--benchmark-id",
    default=None,
    help="Filter by benchmark UUID.",
)
@click.option(
    "--benchmark-version",
    default=None,
    help="Filter by benchmark version string.",
)
@click.option(
    "--target-model",
    default=None,
    help="Filter by target model name.",
)
@click.option(
    "--limit",
    default=50,
    type=int,
    help="Maximum number of results per page (default: 50).",
)
@click.option(
    "--offset",
    default=0,
    type=int,
    help="Number of results to skip (default: 0).",
)
def list_cmd(
    ctx: Context,
    status: str | None,
    benchmark_id: str | None,
    benchmark_version: str | None,
    target_model: str | None,
    limit: int,
    offset: int,
) -> None:
    """List execution run reports.

    Calls GET /api/v1/reports/runs through the SDK with optional filters.
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
            page = client.list_report_runs(
                status=status,
                benchmark_id=benchmark_id,
                benchmark_version=benchmark_version,
                target_model=target_model,
                limit=limit,
                offset=offset,
            )
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        result = {
            "items": [item.model_dump(mode="json") for item in page.items],
            "total": page.total,
            "page": page.page,
            "size": page.size,
        }
        render_json(result)
    elif output_mode == "quiet":
        pass
    else:
        if not page.items:
            click.echo("  (no reports)")
            return
        headers = ["Run ID", "Model", "Version", "Status", "Score", "Completed"]
        rows_data: list[list[str]] = []
        for item in page.items:
            short_id = str(item.run_id)[:8]
            score = f"{item.overall_score:.1f}" if item.overall_score is not None else "-"
            completed = (
                item.completed_at.strftime("%Y-%m-%d %H:%M") if item.completed_at else "-"
            )
            rows_data.append([
                short_id,
                item.target_model,
                item.benchmark_version,
                item.evaluation_status,
                score,
                completed,
            ])
        render_table(headers, rows_data, title="Report Runs")
        if page.total > len(page.items):
            shown = len(page.items)
            click.echo(f"  Showing {shown} of {page.total}")
