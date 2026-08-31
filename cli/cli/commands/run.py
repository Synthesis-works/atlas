"""run commands -- submit, get, list, watch, cancel.

Implements:
  atlas run submit <benchmark-version-id>
  atlas run get <execution-id>
  atlas run list
  atlas run watch <execution-id>
  atlas run cancel <execution-id>
"""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

import click
from atlas_sdk.errors import NetworkError, NotFoundError
from atlas_sdk.models.executions import DispatchTarget, ExecutionResponse

from cli.app import Context, _pass_context
from cli.client import build_client
from cli.config import AtlasConfig
from cli.errors import ExitCode
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.table import render_kv, render_table

if TYPE_CHECKING:
    from atlas_sdk import AtlasClient

_TERMINAL_STATES = frozenset({"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"})
_DEFAULT_POLL_INTERVAL = 3.0
_MAX_CONSECUTIVE_FAILURES = 3
_MOCK_MODEL_ALIASES = frozenset({"mock", "mocked"})


def _adapter_kind(target_model: str) -> str:
    """Classify a target model as a mock or real adapter (advisory only)."""
    return "mock" if target_model.strip().lower() in _MOCK_MODEL_ALIASES else "real"


@click.group(name="run")
def run_group() -> None:
    """Execution operations.

    Examples:

      atlas run list --limit 10

      atlas run get <execution-id>

      atlas run submit <benchmark-version-id> --target-model mock

      atlas run submit <benchmark-version-id> --target-model mock --preview

      atlas run watch <execution-id>

      atlas run cancel <execution-id>
    """


@run_group.command(name="submit")
@_pass_context
@click.argument("benchmark_version_id")
@click.option(
    "--target-model",
    required=True,
    help="Target model for the execution (required; must be explicit).",
)
@click.option(
    "--dataset-version-id",
    default=None,
    help="Dataset version ID (default: resolved from benchmark version).",
)
@click.option(
    "--preview",
    is_flag=True,
    default=False,
    help=(
        "Dry-run: print the submission plan (benchmark, version, dataset, "
        "adapter kind) without creating an execution. Read-only — no POST."
    ),
)
def submit_cmd(
    ctx: Context,
    benchmark_version_id: str,
    target_model: str,
    dataset_version_id: str | None,
    preview: bool,
) -> None:
    """Submit an execution for a benchmark version.

    Calls POST /api/v1/benchmarks/{id}/executions through the SDK.  With
    --preview the plan is resolved from the read-only dispatch-targets
    endpoint and nothing is submitted.  --target-model is always required
    (there is no silent default model).

    Examples:

      atlas run submit <benchmark-version-id> --target-model mock

      atlas run submit <benchmark-version-id> --target-model gpt-4o --preview
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
            if preview:
                _render_submit_preview(
                    client,
                    benchmark_version_id,
                    target_model,
                    dataset_version_id,
                    output_mode,
                )
            else:
                execution = client.submit_execution(
                    benchmark_version_id,
                    target_model=target_model,
                    dataset_version_id=dataset_version_id,
                )
    except Exception as exc:
        error_exit(exc, output_mode)

    if preview:
        return

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


def _render_submit_preview(
    client: AtlasClient,
    benchmark_version_id: str,
    target_model: str,
    dataset_version_id: str | None,
    output_mode: str,
) -> None:
    """Resolve and print the submission plan without creating an execution.

    Uses GET /api/v1/executions/dispatch-targets (read-only).  The version
    is eligible only if it appears in the dispatchable set — the exact set
    the backend would accept — and the dataset mirrors the backend's default
    resolution when no explicit override is given.
    """
    targets: list[DispatchTarget] = client.list_dispatch_targets()
    target = next(
        (t for t in targets if str(t.benchmark_version_id) == benchmark_version_id),
        None,
    )
    if target is None:
        raise NotFoundError(
            status=404,
            message=(
                f"benchmark version {benchmark_version_id} is not a dispatchable "
                "target (unknown, unpublished, or not in your organizations)"
            ),
        )

    adapter_kind = _adapter_kind(target_model)
    resolved_dataset = dataset_version_id or (
        str(target.dataset_version_id) if target.dataset_version_id else None
    )
    plan: dict[str, object] = {
        "benchmark_version_id": benchmark_version_id,
        "benchmark_name": target.benchmark_name,
        "version_string": target.version_string,
        "dataset_version_id": resolved_dataset,
        "target_model": target_model,
        "adapter_kind": adapter_kind,
        "preview": True,
        "note": "no execution created (--preview)",
    }

    if output_mode == "json":
        render_json(plan)
    elif output_mode == "quiet":
        pass
    else:
        rows: list[tuple[str, str]] = [
            ("Benchmark Version", benchmark_version_id),
            ("Benchmark Name", target.benchmark_name),
            ("Version", target.version_string),
            ("Dataset Version", resolved_dataset or "(none)"),
            ("Target Model", target_model),
            ("Adapter Kind", adapter_kind),
        ]
        render_kv(rows, title="Execution Plan (preview)")
        click.echo("  No execution created (--preview).")


@run_group.command(name="get")
@_pass_context
@click.argument("execution_id")
def get_cmd(ctx: Context, execution_id: str) -> None:
    """Show details for a single execution.

    Calls GET /api/v1/executions/{id} through the SDK.

    Examples:

      atlas run get <execution-id>
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
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

    Examples:

      atlas run list

      atlas run list --status QUEUED --limit 5
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
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


def _validate_timeout(
    ctx: click.Context, param: click.Parameter, value: float | None
) -> float | None:
    if value is not None and value <= 0:
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
@click.option(
    "--timeout",
    default=None,
    type=float,
    callback=_validate_timeout,
    help=(
        "Wall-clock wait bound in seconds; must be > 0 when set. "
        "Omitted = unbounded (v1 behavior). On expiry exits 9 "
        "(WATCH_TIMEOUT) with the last observed non-terminal state."
    ),
)
def watch_cmd(
    ctx: Context,
    execution_id: str,
    interval: float,
    timeout: float | None,
) -> None:
    """Watch an execution until it reaches a terminal state.

    Polls GET /api/v1/executions/{id} until the execution completes,
    fails, is cancelled, times out, or the --timeout bound is hit.

    Terminal states: COMPLETED, FAILED, CANCELLED, TIMED_OUT.

    With --timeout, watch is bounded by wall clock; on expiry it exits 9
    (WATCH_TIMEOUT) — in JSON mode the last non-terminal state is emitted.

    Examples:

      atlas run watch <execution-id>

      atlas run watch <execution-id> --interval 5

      atlas run watch <execution-id> --timeout 30
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg, timeout=5.0) as client:
            _poll_execution(client, execution_id, interval, output_mode, timeout)
    except KeyboardInterrupt:
        sys.exit(ExitCode.INTERRUPTED)
    except Exception as exc:
        error_exit(exc, output_mode)


def _poll_execution(
    client: AtlasClient,
    execution_id: str,
    interval: float,
    output_mode: str,
    timeout: float | None = None,
) -> None:
    """Poll get_execution until terminal, the wall-clock bound, or unrecoverable error.

    This is the core watch loop, separated for testability.
    """
    consecutive_failures = 0
    last_execution = None
    deadline = None if timeout is None else time.monotonic() + timeout

    while True:
        if deadline is not None and time.monotonic() >= deadline:
            _exit_watch_timeout(last_execution, timeout, output_mode)

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

        if deadline is None:
            time.sleep(interval)
            continue

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            continue
        time.sleep(min(interval, remaining))


def _exit_watch_timeout(
    last_execution: ExecutionResponse | None,
    timeout: float | None,
    output_mode: str,
) -> None:
    """Exit 9 (WATCH_TIMEOUT), surfacing the last observed non-terminal state."""
    label = f"{timeout:g}" if timeout is not None else "0"
    if output_mode == "json" and last_execution is not None:
        render_json(last_execution.model_dump(mode="json"))
    elif output_mode == "human":
        if last_execution is not None:
            progress = f"{last_execution.completed_items}/{last_execution.total_items}"
            click.echo(
                f"  timed out after {label}s — status {last_execution.status} "
                f"({progress} items); re-run with a larger --timeout",
                err=True,
            )
        else:
            click.echo(
                f"  timed out after {label}s — no state observed; "
                f"re-run with a larger --timeout",
                err=True,
            )
    sys.exit(ExitCode.WATCH_TIMEOUT)


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


@run_group.command(name="cancel")
@_pass_context
@click.argument("execution_id")
def cancel_cmd(ctx: Context, execution_id: str) -> None:
    """Request cancellation of a running or queued execution.

    The backend sets a cancellation flag; the worker transitions the
    execution to CANCELLED cooperatively.  The returned status may
    still be non-terminal (e.g. CANCELLING, RUNNING) if the worker
    has not yet processed the flag.

    Rejects executions already in a terminal state (HTTP 409).

    Examples:

      atlas run cancel <execution-id>
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
            execution = client.cancel_execution(execution_id)
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
            ("Created", execution.created_at.isoformat()),
        ]
        if execution.started_at:
            rows.append(("Started", execution.started_at.isoformat()))
        if execution.completed_at:
            rows.append(("Completed", execution.completed_at.isoformat()))
        render_kv(rows, title="Cancellation Requested")
