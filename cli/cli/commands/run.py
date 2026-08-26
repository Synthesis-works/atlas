"""run commands — submit (Phase 1).

Implements:
  atlas run submit <benchmark-version-id>
  atlas run submit <benchmark-version-id> --output json
  atlas run submit <benchmark-version-id> --quiet
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
