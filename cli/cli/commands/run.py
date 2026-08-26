"""run commands -- submit, get (Phase 1).

Implements:
  atlas run submit <benchmark-version-id>
  atlas run get <execution-id>
"""

from __future__ import annotations

import sys

import click
from atlas_sdk import AtlasClient, StaticTokenSupplier

from cli.app import Context, _pass_context
from cli.config import AtlasConfig
from cli.errors import exit_code_for_error
from cli.output.json import render_json, render_json_error
from cli.output.table import render_kv


@click.group(name="run")
def run_group() -> None:
    """Execution operations."""


def _error_exit(exc: Exception, output_mode: str) -> None:
    """Render an SDK error and exit with the appropriate code."""
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


@run_group.command(name="submit")
@_pass_context
@click.argument("benchmark_version_id")
@click.option(
    "--target-model",
    default="gemini-2.5-flash",
    help="Target model for the execution (default: gemini-2.5-flash).",
)
@click.option(
    "--dataset-version-id",
    default=None,
    help="Dataset version ID (default: resolved from benchmark version).",
)
def submit_cmd(
    ctx: Context,
    benchmark_version_id: str,
    target_model: str,
    dataset_version_id: str | None,
) -> None:
    """Submit an execution for a benchmark version.

    Calls POST /api/v1/benchmarks/{id}/executions through the SDK.
    The execution is created in QUEUED state and dispatched asynchronously.
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
            execution = client.submit_execution(
                benchmark_version_id,
                target_model=target_model,
                dataset_version_id=dataset_version_id,
            )
    except Exception as exc:
        _error_exit(exc, output_mode)

    if output_mode == "json":
        render_json(execution.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        rows: list[tuple[str, str]] = [
            ("Execution ID", str(execution.id)),
            ("Status", execution.status),
            ("Target Model", execution.target_model),
            ("Benchmark Version", str(execution.benchmark_version_id)),
            ("Total Items", str(execution.total_items)),
            ("Max Retries", str(execution.max_retries)),
            ("Created", execution.created_at.isoformat()),
        ]
        render_kv(rows, title="Execution Submitted")


@run_group.command(name="get")
@_pass_context
@click.argument("execution_id")
def get_cmd(ctx: Context, execution_id: str) -> None:
    """Show details for a single execution.

    Calls GET /api/v1/executions/{id} through the SDK.
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
            execution = client.get_execution(execution_id)
    except Exception as exc:
        _error_exit(exc, output_mode)

    if output_mode == "json":
        render_json(execution.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        rows: list[tuple[str, str]] = [
            ("Execution ID", str(execution.id)),
            ("Status", execution.status),
            ("Target Model", execution.target_model),
            ("Benchmark Version", str(execution.benchmark_version_id)),
            ("Progress", f"{execution.completed_items}/{execution.total_items}"),
            ("Max Retries", str(execution.max_retries)),
            ("Created", execution.created_at.isoformat()),
            ("Updated", execution.updated_at.isoformat()),
        ]
        if execution.started_at:
            rows.append(("Started", execution.started_at.isoformat()))
        if execution.completed_at:
            rows.append(("Completed", execution.completed_at.isoformat()))
        if execution.attempts:
            rows.append(("Attempts", str(len(execution.attempts))))
        render_kv(rows, title="Execution")
