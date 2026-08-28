"""leaderboard commands.

Implements:
  atlas leaderboard benchmark <benchmark-version-id>
  atlas leaderboard benchmark <benchmark-version-id> --limit 20
  atlas leaderboard benchmark <benchmark-version-id> --offset 20
  atlas leaderboard benchmark <benchmark-version-id> --output json
  atlas leaderboard benchmark <benchmark-version-id> --quiet
  atlas leaderboard model <model-name>
  atlas leaderboard model <model-name> --history
  atlas leaderboard model <model-name> --benchmarks
  atlas leaderboard model <model-name> --output json
  atlas leaderboard model <model-name> --quiet
"""

from __future__ import annotations

import click
from atlas_sdk import (
    AtlasClient,
    ModelBenchmarkHistory,
    ModelSummary,
    StaticTokenSupplier,
    TrendPoint,
)

from cli.app import Context, _pass_context
from cli.config import AtlasConfig
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.table import render_kv, render_table


@click.group(name="leaderboard")
def leaderboard_group() -> None:
    """Leaderboard operations.

    Examples:

      atlas leaderboard benchmark <benchmark-version-id>

      atlas leaderboard model mock

      atlas leaderboard model mock --history

      atlas leaderboard model mock --benchmarks
    """


@leaderboard_group.command(name="benchmark")
@_pass_context
@click.argument("benchmark_version_id")
@click.option(
    "--limit",
    default=20,
    type=int,
    help="Maximum number of entries (default: 20).",
)
@click.option(
    "--offset",
    default=0,
    type=int,
    help="Number of entries to skip (default: 0).",
)
def benchmark_cmd(
    ctx: Context,
    benchmark_version_id: str,
    limit: int,
    offset: int,
) -> None:
    """Show the ranked leaderboard for a benchmark version.

    BENCHMARK_VERSION_ID is the benchmark version UUID.

    Calls GET /api/v1/benchmarks/{benchmark_version_id}/leaderboard
    through the SDK.

    Examples:

      atlas leaderboard benchmark <benchmark-version-id>

      atlas leaderboard benchmark <benchmark-version-id> --limit 50
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
            leaderboard = client.get_benchmark_leaderboard(
                benchmark_version_id,
                limit=limit,
                offset=offset,
            )
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        render_json(leaderboard.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        entries = leaderboard.entries
        if not entries.items:
            click.echo("  (no entries)")
            return

        rows_data: list[list[str]] = []
        for item in entries.items:
            updated = item.last_updated.strftime("%Y-%m-%d %H:%M")
            rank_delta = str(item.rank_delta) if item.rank_delta is not None else "-"
            rows_data.append([
                str(item.rank),
                item.model_name,
                f"{item.overall_score:.2f}",
                str(item.benchmark_count),
                updated,
                rank_delta,
            ])
        render_table(
            ["Rank", "Model", "Score", "# Benchmarks", "Updated", "Rank Delta"],
            rows_data,
            title=leaderboard.title,
        )
        if entries.total > len(entries.items):
            shown = len(entries.items)
            click.echo(f"  Showing {shown} of {entries.total}")


@leaderboard_group.command(name="model")
@_pass_context
@click.argument("model_name")
@click.option(
    "--history",
    is_flag=True,
    help="Show the model's execution history instead of the summary.",
)
@click.option(
    "--benchmarks",
    is_flag=True,
    help="Show the model's per-benchmark history breakdown.",
)
def model_cmd(
    ctx: Context,
    model_name: str,
    history: bool,
    benchmarks: bool,
) -> None:
    """Show the overall performance profile for a model.

    MODEL_NAME is the model identifier (e.g. "mock").

    Without --history, calls GET /api/v1/models/{model_name}/summary.
    With --history, calls GET /api/v1/models/{model_name}/history.
    With --benchmarks, calls GET /api/v1/models/{model_name}/benchmarks.
    Unknown model names return "no data" (exit 0), not an error.

    Examples:

      atlas leaderboard model mock

      atlas leaderboard model mock --history

      atlas leaderboard model mock --benchmarks
    """
    if history and benchmarks:
        raise click.UsageError(
            "--history and --benchmarks are mutually exclusive."
        )

    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    supplier = StaticTokenSupplier(cfg.token) if cfg.token else None

    try:
        with AtlasClient(
            cfg.base_url,
            token_supplier=supplier,
            timeout=cfg.timeout,
        ) as client:
            if history:
                points = client.get_model_history(model_name)
            elif benchmarks:
                entries = client.get_model_benchmarks(model_name)
            else:
                summary = client.get_model_summary(model_name)
    except Exception as exc:
        error_exit(exc, output_mode)

    if history:
        _render_history(points, model_name, output_mode)
    elif benchmarks:
        _render_benchmarks(entries, model_name, output_mode)
    else:
        _render_summary(summary, output_mode)


def _render_summary(summary: ModelSummary, output_mode: str) -> None:
    if output_mode == "json":
        render_json(summary.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        if summary.benchmarks == 0:
            click.echo(f"  No benchmark data for model '{summary.model}'")
            return

        rows: list[tuple[str, str]] = [
            ("Model", summary.model),
            ("Benchmarks", str(summary.benchmarks)),
        ]
        if summary.best_rank is not None:
            rows.append(("Best Rank", str(summary.best_rank)))
        if summary.average_rank is not None:
            rows.append(("Avg Rank", f"{summary.average_rank:.2f}"))
        if summary.average_score is not None:
            rows.append(("Avg Score", f"{summary.average_score:.2f}"))
        if summary.last_execution is not None:
            rows.append(("Updated", summary.last_execution.strftime("%Y-%m-%d %H:%M")))
        if summary.latest_delta is not None:
            rows.append(("Delta", f"{summary.latest_delta:+d}"))
        render_kv(rows, title="Model Summary")


def _render_history(points: list[TrendPoint], model_name: str, output_mode: str) -> None:
    if output_mode == "json":
        render_json([point.model_dump(mode="json") for point in points])
    elif output_mode == "quiet":
        pass
    else:
        if not points:
            click.echo(f"  No history for model '{model_name}'")
            return

        rows_data: list[list[str]] = []
        for point in points:
            rows_data.append([
                point.timestamp.strftime("%Y-%m-%d %H:%M"),
                f"{point.score:.2f}",
                str(point.rank) if point.rank is not None else "-",
                point.benchmark_version if point.benchmark_version is not None else "-",
                point.execution_id,
            ])
        render_table(
            ["Timestamp", "Score", "Rank", "Benchmark", "Execution"],
            rows_data,
            title=f"Model History: {model_name}",
        )


def _render_benchmarks(
    entries: list[ModelBenchmarkHistory],
    model_name: str,
    output_mode: str,
) -> None:
    if output_mode == "json":
        render_json([entry.model_dump(mode="json") for entry in entries])
    elif output_mode == "quiet":
        pass
    else:
        if not entries:
            click.echo(f"  No benchmark data for model '{model_name}'")
            return

        rows_data: list[list[str]] = []
        for entry in entries:
            all_points = [p for v in entry.versions for p in v.history]
            total_runs = len(all_points)
            num_versions = len(entry.versions)

            latest = max(
                all_points,
                key=lambda p: (p.timestamp, str(p.execution_id)),
            )
            rows_data.append([
                entry.benchmark_name,
                str(num_versions),
                str(total_runs),
                f"{latest.score:.2f}",
                latest.timestamp.strftime("%Y-%m-%d %H:%M"),
            ])

        rows_data.sort(key=lambda row: row[0])
        render_table(
            ["Benchmark", "Versions", "Runs", "Latest Score", "Updated"],
            rows_data,
            title=f"Model Benchmarks: {model_name}",
        )
