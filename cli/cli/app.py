"""atlas CLI — root entry point and global options (§5, §9.1).

Global flags: --output, --profile, --timeout, --no-color, --quiet, --version, --help
"""

from __future__ import annotations

import click

from cli import __version__
from cli.config import AtlasConfig, load_config


class Context:
    """Per-invocation state passed to subcommands via Click context."""

    def __init__(self) -> None:
        self.config: AtlasConfig = load_config()


_pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group(invoke_without_command=True)
@click.option(
    "--output",
    "-o",
    "output_mode",
    type=click.Choice(["human", "json", "quiet"], case_sensitive=False),
    default=None,
    help="Output mode (default: human).",
)
@click.option(
    "--base-url",
    default=None,
    envvar="ATLAS_BASE_URL",
    help="Atlas API base URL (default: http://localhost:8000).",
)
@click.option(
    "--profile",
    default=None,
    envvar="ATLAS_PROFILE",
    help="Configuration profile name.",
)
@click.option(
    "--timeout",
    default=None,
    type=float,
    envvar="ATLAS_TIMEOUT",
    help="Request timeout in seconds.",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    help="Disable colored output.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Shorthand for --output quiet.",
)
@click.version_option(__version__, "--version", "-V", prog_name="atlas")
@_pass_context
def main(
    ctx: Context,
    output_mode: str | None,
    base_url: str | None,
    profile: str | None,
    timeout: float | None,
    no_color: bool,
    quiet: bool,
) -> None:
    """Atlas CLI — control-plane interface for the Atlas platform."""
    ctx.config = load_config(
        base_url=base_url,
        output=output_mode,
        profile=profile,
        timeout=timeout,
        no_color=no_color,
        quiet=quiet,
    )
    click_ctx = click.get_current_context()
    if click_ctx.invoked_subcommand is None:
        click.echo(click_ctx.get_help())


# ── command registration ───────────────────────────────────────────────
from cli.commands.auth import login_cmd as _login_cmd  # noqa: E402
from cli.commands.auth import logout_cmd as _logout_cmd  # noqa: E402
from cli.commands.auth import whoami_cmd as _whoami_cmd  # noqa: E402
from cli.commands.benchmark import benchmark_group as _benchmark_group  # noqa: E402
from cli.commands.health import health_cmd as _health_cmd  # noqa: E402
from cli.commands.leaderboard import leaderboard_group as _leaderboard_group  # noqa: E402
from cli.commands.report import report_group as _report_group  # noqa: E402
from cli.commands.run import run_group as _run_group  # noqa: E402

main.add_command(_login_cmd)  # type: ignore[has-type]
main.add_command(_logout_cmd)  # type: ignore[has-type]
main.add_command(_whoami_cmd)  # type: ignore[has-type]
main.add_command(_benchmark_group)  # type: ignore[has-type]
main.add_command(_health_cmd)  # type: ignore[has-type]
main.add_command(_leaderboard_group)  # type: ignore[has-type]
main.add_command(_report_group)  # type: ignore[has-type]
main.add_command(_run_group)  # type: ignore[has-type]


def entrypoint() -> None:
    """Package entry point (referenced in pyproject.toml)."""
    main(standalone_mode=False)
