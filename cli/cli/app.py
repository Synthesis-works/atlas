"""atlas CLI — root entry point and global options (§5, §9.1).

Global flags: --output, --base-url, --profile, --timeout, --retries, --no-color,
--quiet, --version, --help
"""

from __future__ import annotations

import sys

import click

from cli import __version__
from cli.config import AtlasConfig, load_config
from cli.errors import ExitCode
from cli.output.errors import error_exit


def _validate_retries(ctx: click.Context, param: click.Parameter, value: int | None) -> int | None:
    """Reject negative retry counts (applies to both flag and env value)."""
    if value is not None and value < 0:
        raise click.BadParameter("must be >= 0")
    return value


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
    "--retries",
    default=None,
    type=int,
    envvar="ATLAS_RETRIES",
    callback=_validate_retries,
    help="Max retries for idempotent GET/HEAD requests (default: 3). POST is never retried.",
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
    retries: int | None,
    no_color: bool,
    quiet: bool,
) -> None:
    """Atlas CLI — control-plane interface for the Atlas platform.

    Examples:

      atlas login

      atlas health

      atlas dashboard

      atlas leaderboard model mock --history
    """
    ctx.config = load_config(
        base_url=base_url,
        output=output_mode,
        profile=profile,
        timeout=timeout,
        retries=retries,
        no_color=no_color,
        quiet=quiet,
    )
    click_ctx = click.get_current_context()
    if click_ctx.invoked_subcommand is None:
        # A bare, interactive ``atlas`` starts the agent REPL (Gemini-CLI style).
        # Non-TTY / piped invocations keep printing help so automation that
        # runs ``atlas`` for help output is unaffected.
        if _is_tty():
            raise SystemExit(_run_repl(ctx))
        click.echo(click_ctx.get_help())


def _is_tty() -> bool:
    """True only when stdin is an interactive terminal (drives the REPL)."""
    try:
        return bool(sys.stdin.isatty())
    except Exception:  # noqa: BLE001
        return False


def _agent_unavailable_message() -> str:
    return (
        "error: Atlas agent brain unavailable. Set GROQ_API_KEY or GEMINI_API_KEY "
        "to use the Atlas agent."
    )


def _run_repl(ctx: Context) -> int:
    """Start the interactive agent REPL; returns a process exit code."""
    from cli.agent.repl import AgentREPL, build_agent_provider
    from cli.client import build_client

    provider = build_agent_provider()
    if not provider.available:
        click.echo(_agent_unavailable_message(), err=True)
        return ExitCode.AGENT_UNAVAILABLE

    cfg: AtlasConfig = ctx.config
    repl = AgentREPL(
        provider=provider,
        client_factory=lambda: build_client(cfg),
    )
    try:
        return repl.interact()
    except Exception as exc:  # noqa: BLE001
        error_exit(exc, cfg.effective_output())
        raise SystemExit(ExitCode.UNSPECIFIED) from exc


@click.command(name="agent")
@click.argument("task")
@click.option(
    "--provider",
    "provider",
    type=click.Choice(["auto", "groq", "gemini"], case_sensitive=False),
    default="auto",
    show_default=True,
    help=(
        "LLM provider for the agent brain: auto (fallback across configured "
        "providers), groq, or gemini."
    ),
)
@_pass_context
def agent_cmd(ctx: Context, task: str, provider: str) -> None:
    """Run the Atlas agent once over a quoted task (non-interactive).

    Example:

      atlas agent "List the available benchmarks"
    """
    from cli.agent.repl import build_agent_provider, run_one_shot
    from cli.client import build_client

    provider_obj = build_agent_provider(provider_name=provider)
    if not provider_obj.available:
        click.echo(_agent_unavailable_message(), err=True)
        raise SystemExit(ExitCode.AGENT_UNAVAILABLE)

    cfg: AtlasConfig = ctx.config
    try:
        with build_client(cfg) as client:
            code = run_one_shot(task, provider=provider_obj, client=client)
    except Exception as exc:  # noqa: BLE001
        error_exit(exc, cfg.effective_output())
        raise SystemExit(ExitCode.UNSPECIFIED) from exc
    raise SystemExit(code)


# ── command registration ───────────────────────────────────────────────
from cli.commands.activity import activity_cmd as _activity_cmd  # noqa: E402
from cli.commands.auth import login_cmd as _login_cmd  # noqa: E402
from cli.commands.auth import logout_cmd as _logout_cmd  # noqa: E402
from cli.commands.auth import whoami_cmd as _whoami_cmd  # noqa: E402
from cli.commands.benchmark import benchmark_group as _benchmark_group  # noqa: E402
from cli.commands.dashboard import dashboard_cmd as _dashboard_cmd  # noqa: E402
from cli.commands.health import health_cmd as _health_cmd  # noqa: E402
from cli.commands.leaderboard import leaderboard_group as _leaderboard_group  # noqa: E402
from cli.commands.models import model_group as _model_group  # noqa: E402
from cli.commands.report import report_group as _report_group  # noqa: E402
from cli.commands.run import run_group as _run_group  # noqa: E402

main.add_command(agent_cmd)
main.add_command(_login_cmd)  # type: ignore[has-type]
main.add_command(_logout_cmd)  # type: ignore[has-type]
main.add_command(_whoami_cmd)  # type: ignore[has-type]
main.add_command(_activity_cmd)  # type: ignore[has-type]
main.add_command(_benchmark_group)  # type: ignore[has-type]
main.add_command(_dashboard_cmd)  # type: ignore[has-type]
main.add_command(_health_cmd)  # type: ignore[has-type]
main.add_command(_leaderboard_group)  # type: ignore[has-type]
main.add_command(_model_group)  # type: ignore[has-type]
main.add_command(_report_group)  # type: ignore[has-type]
main.add_command(_run_group)  # type: ignore[has-type]


def entrypoint() -> None:
    """Package entry point (referenced in pyproject.toml)."""
    try:
        main(standalone_mode=False)
    except click.ClickException as exc:
        # click raises UsageError/BadParameter/MissingParameter for malformed
        # invocations.  With standalone_mode=False those are NOT handled by
        # click itself, so surface a clean message and the documented exit
        # code (2 for usage errors) instead of a raw traceback.
        click.echo(f"Error: {exc.format_message()}", err=True)
        raise SystemExit(exc.exit_code) from exc
