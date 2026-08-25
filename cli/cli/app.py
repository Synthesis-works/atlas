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


def get_config() -> AtlasConfig:
    """Retrieve the resolved config from the current Click context."""
    ctx = click.get_current_context()
    return ctx.find_object(Context).config  # type: ignore[union-attr]


def handle_command_errors(func: object) -> None:  # type: ignore[type-arg]
    """Raise so that the caller can catch and exit appropriately.

    This is not a decorator — it is called at the entrypoint level.
    Individual commands should call this via the entrypoint wrapper.
    """


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
    profile: str | None,
    timeout: float | None,
    no_color: bool,
    quiet: bool,
) -> None:
    """Atlas CLI — control-plane interface for the Atlas platform."""
    ctx.config = load_config(
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
from cli.commands.auth import whoami_cmd as _whoami_cmd  # noqa: E402
from cli.commands.health import health_cmd as _health_cmd  # noqa: E402

main.add_command(_whoami_cmd)  # type: ignore[has-type]
main.add_command(_health_cmd)  # type: ignore[has-type]


def entrypoint() -> None:
    """Package entry point (referenced in pyproject.toml)."""
    main(standalone_mode=False)
