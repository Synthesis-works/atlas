"""leaderboard commands.

Implements:
  atlas leaderboard benchmark <benchmark-version-id>
  atlas leaderboard benchmark <benchmark-version-id> --limit 20
  atlas leaderboard benchmark <benchmark-version-id> --offset 20
  atlas leaderboard benchmark <benchmark-version-id> --output json
  atlas leaderboard benchmark <benchmark-version-id> --quiet
  atlas leaderboard model <model-name>
  atlas leaderboard model <model-name> --output json
  atlas leaderboard model <model-name> --quiet
"""

from __future__ import annotations

import click
from atlas_sdk import AtlasClient, StaticTokenSupplier

from cli.app import Context, _pass_context
from cli.config import AtlasConfig
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.table import render_kv, render_table


@click.group(name="leaderboard")
def leaderboard_group() -> None:
    """Leaderboard operations."""


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
def model_cmd(ctx: Context, model_name: str) -> None:
    """Show the overall performance summary for a model.

    MODEL_NAME is the model identifier (e.g. "mock").

    Calls GET /api/v1/models/{model_name}/summary through the SDK.
    Unknown model names return a zeroed summary (exit 0), not an error.
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
            summary = client.get_model_summary(model_name)
    except Exception as exc:
        error_exit(exc, output_mode)

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
