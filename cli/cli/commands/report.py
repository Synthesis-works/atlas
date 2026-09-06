"""report commands -- list, get, export (Phase 1).

Implements:
  atlas report list
  atlas report list --output json
  atlas report list --quiet
  atlas report get <run-id>
  atlas report get <run-id> --output json
  atlas report get <run-id> --quiet
  atlas report export <run-id>
  atlas report export <run-id> --format csv
  atlas report export <run-id> --output-file report.json
  atlas report export <run-id> --output-file -
  atlas report export <run-id> --include-prompt
  atlas report export <run-id> --include-expected-output
  atlas report export <run-id> --force
"""

from __future__ import annotations

import os
import sys

import click
from atlas_sdk import ReportSummaryRead
from atlas_sdk.errors import ConflictError

from cli.app import Context, _pass_context
from cli.client import build_client
from cli.config import AtlasConfig
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.schema import emit_json_schema
from cli.output.table import render_kv, render_table


@click.group(name="report")
def report_group() -> None:
    """Report operations.

    Examples:

      atlas report list --limit 10

      atlas report get <run-id>

      atlas report export <run-id> --format csv --output-file report.csv
    """


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

    Examples:

      atlas report list

      atlas report list --status COMPLETED --limit 10
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
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
            completed = item.completed_at.strftime("%Y-%m-%d %H:%M") if item.completed_at else "-"
            rows_data.append(
                [
                    short_id,
                    item.target_model,
                    item.benchmark_version,
                    item.evaluation_status,
                    score,
                    completed,
                ]
            )
        render_table(headers, rows_data, title="Report Runs")
        if page.total > len(page.items):
            shown = len(page.items)
            click.echo(f"  Showing {shown} of {page.total}")


@report_group.command(name="get")
@click.option(
    "--json-schema",
    is_flag=True,
    default=False,
    help="Print the JSON Schema of this command's JSON output (offline) and exit.",
)
@_pass_context
@click.argument("run_id")
def get_cmd(ctx: Context, run_id: str, json_schema: bool) -> None:
    """Fetch the detailed report for a single execution run.

    RUN_ID is the execution run UUID.
    Calls GET /api/v1/reports/runs/{run_id} through the SDK.

    Examples:

      atlas report get <run-id>

      atlas report get <run-id> --json-schema
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    if json_schema:
        emit_json_schema(ReportSummaryRead, output_mode=output_mode)
        return

    try:
        with build_client(cfg) as client:
            summary = client.get_report_run(run_id)
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        render_json(summary.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        started = summary.started_at.strftime("%Y-%m-%d %H:%M") if summary.started_at else "-"
        completed = summary.completed_at.strftime("%Y-%m-%d %H:%M") if summary.completed_at else "-"
        score = f"{summary.overall_score:.1f}" if summary.overall_score is not None else "-"

        render_kv(
            [
                ("Run ID", str(summary.run_id)),
                ("Benchmark", summary.benchmark_name),
                ("Version", summary.benchmark_version),
                ("Model", summary.target_model),
                ("Status", summary.evaluation_status),
                ("Started", started),
                ("Completed", completed),
                ("Overall Score", score),
            ],
            title="Report Summary",
        )

        if summary.scores:
            rows_data = [[item.capability_name, f"{item.score:.1f}"] for item in summary.scores]
            render_table(["Capability", "Score"], rows_data, title="Score Breakdown")


def _ensure_destination(dest: str, force: bool, output_mode: str) -> None:
    """Refuse to overwrite an existing destination unless ``--force``."""
    if os.path.exists(dest) and not force:
        error_exit(
            ConflictError(
                status=409,
                code="CONFLICT",
                message=f"Destination already exists: {dest} (use --force to overwrite).",
            ),
            output_mode,
        )


@report_group.command(name="export")
@_pass_context
@click.argument("run_id")
@click.option(
    "--format",
    "format_type",
    default="json",
    type=click.Choice(["json", "csv"], case_sensitive=False),
    help="Export format (default: json).",
)
@click.option(
    "--output-file",
    default=None,
    help="Destination path, or '-' for raw bytes on stdout "
    "(default: server-provided filename in cwd).",
)
@click.option(
    "--include-prompt",
    is_flag=True,
    default=False,
    help="Include original prompts in the export.",
)
@click.option(
    "--include-expected-output",
    is_flag=True,
    default=False,
    help="Include expected outputs in the export.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite the destination file if it already exists.",
)
def export_cmd(
    ctx: Context,
    run_id: str,
    format_type: str,
    output_file: str | None,
    include_prompt: bool,
    include_expected_output: bool,
    force: bool,
) -> None:
    """Export the report for a single execution run.

    RUN_ID is the execution run UUID.
    Calls GET /api/v1/reports/runs/{run_id}/export through the SDK and writes
    the raw response bytes to a file (or stdout with --output-file -).

    Examples:

      atlas report export <run-id>

      atlas report export <run-id> --format csv --output-file report.csv

      atlas report export <run-id> --output-file - > report.json
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
            result = client.export_report_run(
                run_id,
                format_type=format_type,
                include_prompt=include_prompt,
                include_expected_output=include_expected_output,
            )
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_file == "-":
        # Raw payload only on stdout — never mix receipts into this stream.
        sys.stdout.buffer.write(result.content)
        sys.stdout.buffer.flush()
        return

    dest = output_file or result.filename or f"report-{run_id}.{format_type}"
    _ensure_destination(dest, force, output_mode)

    with open(dest, "wb") as fh:
        fh.write(result.content)

    if output_mode == "json":
        render_json(
            {
                "path": dest,
                "bytes": len(result.content),
                "content_type": result.content_type,
            }
        )
    elif output_mode == "quiet":
        pass
    else:
        click.echo(f"Exported report to {dest} ({len(result.content)} bytes)")
