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


class _AgentFirstGroup(click.Group):
    """Root group whose first non-option token is treated as natural language.

    Resolution order is strict and stable:

    1. ``--help`` / ``--version`` / any global option (parsed by the group's
       own option parser *before* command resolution; consumed there).
    2. A registered deterministic command — ``login``, ``benchmark``,
       ``run``, ``agent``, etc. — wins on the FIRST token, always.
    3. Anything else (unknown first token, or a quoted/multi-word phrase) is
       routed to the hidden ``_nlu`` command, which sends the whole remainder
       as a prompt to the hosted agent — ``atlas "run the mock suite"`` and
       ``atlas help me`` both work, while ``atlas run the mock suite`` stays a
       deterministic ``run`` invocation (its own usage error), so future
       commands never change meaning.
    """

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str, click.Command, list[str]]:
        token = args[0] if args else None
        if token is None or token.startswith("-"):
            # No tokens (bare ``atlas``) or a leftover option-like token:
            # nothing to route here (the group's own options were already
            # consumed by its option parser before this is reached).
            raise click.NoSuchCommand(token or "")
        known = self.get_command(ctx, token)
        if known is not None:
            return token, known, args[1:]
        # Not a command → agent-first: hand the FULL argument list to _nlu so
        # every token after ``atlas`` is interpreted as natural language.
        nlu = self.get_command(ctx, "_nlu")
        if nlu is not None:
            return "_nlu", nlu, args
        raise click.NoSuchCommand(token)


@click.group(cls=_AgentFirstGroup, invoke_without_command=True)
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
    help="Atlas API base URL (default: the hosted Atlas API).",
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

      atlas "run the mock benchmark suite"

    With no command, ``atlas`` starts the interactive agent: the hosted Atlas
    conversation when you are signed in, otherwise the local BYOK loop.  With
    a quoted (or multi-word) non-command first token, the whole phrase is sent
    to the hosted agent as a one-shot request.
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
    """BYOK-only guidance (used by ``atlas agent``)."""
    from cli.agent.setup import missing_key_message

    return missing_key_message()


def _hosted_unavailable_message() -> str:
    """Guidance for conversational paths when neither auth nor BYOK keys exist."""
    from cli.agent.setup import hosted_unavailable_message

    return hosted_unavailable_message()


def _run_repl(ctx: Context) -> int:
    """Start the conversational agent REPL; returns a process exit code.

    Hosted-first: when an Atlas session token is present the REPL drives the
    hosted brain through the P1 session API (provider keys stay on the
    server).  Without auth it falls back to the existing BYOK local loop so a
    keyed set-up keeps working.  With neither, prints actionable guidance and
    exits 10.
    """
    cfg: AtlasConfig = ctx.config

    def _byok_repl() -> int:
        from cli.agent.repl import AgentREPL, build_agent_provider
        from cli.client import build_client

        provider = build_agent_provider()
        if not provider.available:
            click.echo(_hosted_unavailable_message(), err=True)
            return ExitCode.AGENT_UNAVAILABLE
        repl = AgentREPL(provider=provider, client_factory=lambda: build_client(cfg))
        try:
            return repl.interact()
        except Exception as exc:  # noqa: BLE001
            error_exit(exc, cfg.effective_output())
            return ExitCode.UNSPECIFIED

    if not cfg.token:
        return _byok_repl()

    from cli.agent.hosted import HostedAgentREPL
    from cli.client import build_client

    try:
        with build_client(cfg) as client:
            return HostedAgentREPL(client).interact()
    except Exception as exc:  # noqa: BLE001
        error_exit(exc, cfg.effective_output())
        return ExitCode.UNSPECIFIED


@click.command(name="_nlu", hidden=True)
@click.argument("words", nargs=-1, required=True)
@_pass_context
def _nlu(ctx: Context, words: tuple[str, ...]) -> None:
    """Agent-first fallback: send the remaining tokens as natural language.

    Hidden from ``--help``; only reachable via the ``_AgentFirstGroup``
    routing for unknown first tokens (bare ``atlas`` is handled separately).
    Requires an Atlas session; without one it prints guidance and exits 10.
    """
    from cli.agent.hosted import run_hosted_one_shot
    from cli.client import build_client

    cfg: AtlasConfig = ctx.config
    if not cfg.token:
        click.echo(_hosted_unavailable_message(), err=True)
        raise SystemExit(ExitCode.AGENT_UNAVAILABLE)
    task = " ".join(words)
    try:
        with build_client(cfg) as client:
            code = run_hosted_one_shot(client, task)
    except Exception as exc:  # noqa: BLE001
        error_exit(exc, cfg.effective_output())
        raise SystemExit(ExitCode.UNSPECIFIED) from exc
    raise SystemExit(code)


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
main.add_command(_nlu)
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
