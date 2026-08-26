"""run commands -- submit, get, list, watch (Phase 1/2).

Implements:
  atlas run submit <benchmark-version-id>
  atlas run get <execution-id>
  atlas run list
  atlas run watch <execution-id>
"""

from __future__ import annotations

import sys
import time

import click
from atlas_sdk import AtlasClient, StaticTokenSupplier
from atlas_sdk.errors import NetworkError
from atlas_sdk.models.executions import ExecutionResponse

from cli.app import Context, _pass_context
from cli.config import AtlasConfig
from cli.errors import ExitCode
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.table import render_kv, render_table

_TERMINAL_STATES = frozenset({"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"})
_DEFAULT_POLL_INTERVAL = 3.0
_MAX_CONSECUTIVE_FAILURES = 3


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
        error_exit(exc, output_mode)

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
        error_exit(exc, output_mode)

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


@run_group.command(name="list")
@_pass_context
@click.option(
    "--benchmark-version-id",
    default=None,
    help="Filter by benchmark version UUID.",
)
@click.option(
    "--status",
    default=None,
    help="Filter by execution status (e.g. QUEUED, RUNNING, COMPLETED).",
)
@click.option(
    "--limit",
    default=20,
    type=int,
    help="Maximum number of executions to return (default: 20).",
)
@click.option(
    "--offset",
    default=0,
    type=int,
    help="Number of executions to skip (default: 0).",
)
def list_cmd(
    ctx: Context,
    benchmark_version_id: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> None:
    """List executions.

    Calls GET /api/v1/executions through the SDK with optional filters.
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
            page = client.list_executions(
                benchmark_version_id=benchmark_version_id,
                status=status,
                limit=limit,
                offset=offset,
            )
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        result = {
            "items": [e.model_dump(mode="json") for e in page.items],
            "total": page.total,
            "limit": page.limit,
            "offset": page.offset,
        }
        render_json(result)
    elif output_mode == "quiet":
        pass
    else:
        if not page.items:
            click.echo("No executions found.")
            return
        headers = ["ID", "Status", "Model", "Progress", "Created"]
        rows_data: list[list[str]] = []
        for e in page.items:
            short_id = str(e.id)[:8]
            progress = f"{e.completed_items}/{e.total_items}"
            created = e.created_at.strftime("%Y-%m-%d %H:%M")
            rows_data.append([
                short_id,
                e.status,
                e.target_model,
                progress,
                created,
            ])
        render_table(headers, rows_data, title="Executions")
        if page.total > len(page.items):
            shown = len(page.items)
            click.echo(f"  Showing {shown} of {page.total}")


def _validate_interval(ctx: click.Context, param: click.Parameter, value: float) -> float:
    if value <= 0:
        raise click.BadParameter("must be greater than 0")
    return value


@run_group.command(name="watch")
@_pass_context
@click.argument("execution_id")
@click.option(
    "--interval",
    default=_DEFAULT_POLL_INTERVAL,
    type=float,
    callback=_validate_interval,
    is_eager=False,
    help=f"Polling interval in seconds (default: {_DEFAULT_POLL_INTERVAL}).",
)
def watch_cmd(ctx: Context, execution_id: str, interval: float) -> None:
    """Watch an execution until it reaches a terminal state.

    Polls GET /api/v1/executions/{id} until the execution completes,
    fails, is cancelled, or times out.

    Terminal states: COMPLETED, FAILED, CANCELLED, TIMED_OUT.
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    supplier = StaticTokenSupplier(cfg.token) if cfg.token else None

    try:
        with AtlasClient(
            cfg.base_url,
            token_supplier=supplier,
            timeout=5.0,
        ) as client:
            _poll_execution(client, execution_id, interval, output_mode)
    except KeyboardInterrupt:
        sys.exit(ExitCode.INTERRUPTED)
    except Exception as exc:
        error_exit(exc, output_mode)


def _poll_execution(
    client: AtlasClient,
    execution_id: str,
    interval: float,
    output_mode: str,
) -> None:
    """Poll get_execution until terminal or unrecoverable error.

    This is the core watch loop, separated for testability.
    """
    consecutive_failures = 0
    last_execution = None

    while True:
        try:
            execution = client.get_execution(execution_id)
            consecutive_failures = 0
            last_execution = execution

            if execution.status in _TERMINAL_STATES:
                _render_watch_final(execution, output_mode)
                return

            if output_mode == "human":
                progress = f"{execution.completed_items}/{execution.total_items}"
                click.echo(
                    f"  [{execution.status}] {progress} — waiting {interval:.0f}s...",
                    err=True,
                )

        except NetworkError:
            consecutive_failures += 1
            if output_mode == "human":
                click.echo(
                    f"  [network error] attempt "
                    f"{consecutive_failures}/{_MAX_CONSECUTIVE_FAILURES}"
                    f" — retrying...",
                    err=True,
                )
            if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                if last_execution is not None and output_mode == "json":
                    render_json(last_execution.model_dump(mode="json"))
                sys.exit(ExitCode.UNSPECIFIED)

        time.sleep(interval)


def _render_watch_final(execution: ExecutionResponse, output_mode: str) -> None:
    """Render the final execution state for watch."""
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
            ("Created", execution.created_at.isoformat()),
        ]
        if execution.started_at:
            rows.append(("Started", execution.started_at.isoformat()))
        if execution.completed_at:
            rows.append(("Completed", execution.completed_at.isoformat()))
        render_kv(rows, title="Execution Complete")
