"""Client-side agent REPL + one-shot runner (Phase 4).

Interactive (``atlas`` with a TTY) and non-interactive (``atlas agent "task"``)
surfaces on top of the Phase 3 ``AgentLoop``.

Interactive REPL
    You > ...    (user turn, read from stdin with Ctrl-C/EOF clean exit)
    Atlas > ...  (final response)
    ✓ tool       (progress line per tool call)
    WRITE tools are gated behind a confirmation prompt before execution; a
    rejected mutation is recorded as a structured "declined" observation so the
    agent sees the user declined rather than a tool failure.  READ tools never
    prompt.

One-shot
    ``atlas agent "task"`` runs the loop once with auto-approval (no prompts).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import click

from cli.agent.loop import AgentLoop
from cli.agent.tools.registry import ToolRegistry
from cli.errors import ExitCode

_STOP_COMMANDS = {"exit", "quit", "q"}


def _progress_glyphs() -> tuple[str, str]:
    """Return (ok, fail) markers safe for the target stream encoding.

    ``✓``/``✗`` on a UTF-8 terminal; ``[ok]``/``[!]`` where unicode can't be
    encoded (e.g. a Windows cp1252 console), so a tool-call progress line never
    crashes the REPL with a ``UnicodeEncodeError``.
    """
    try:
        stream_encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        "\u2713".encode(stream_encoding)
        return "\u2713", "\u2717"
    except (UnicodeEncodeError, LookupError, AttributeError):
        return "[ok]", "[!]"


_PROGRESS_OK, _PROGRESS_FAIL = _progress_glyphs()


def build_agent_provider(
    *,
    model: str | None = None,
    api_key_env: str = "GEMINI_API_KEY",
    provider_name: str | None = None,
) -> Any:
    """Construct the agent's LLM provider (a ``ProviderRouter``, v3.1).

    ``provider_name`` selects an explicit provider ("groq", "gemini"); ``auto``
    (or omitted) builds a fallback router that tries available providers in
    order.  ``available`` reflects whether at least one brain is configured; the
    app checks it to refuse to start with exit code 10 when unavailable.
    """
    from cli.agent.provider import GeminiProvider, GroqProvider
    from cli.agent.router import ProviderRouter

    agent_model = model or os.environ.get("AGENT_MODEL")
    gemini = GeminiProvider(model=agent_model, api_key_env=api_key_env)
    groq = GroqProvider(model=os.environ.get("AGENT_GROQ_MODEL"))

    if provider_name and provider_name != "auto":
        return ProviderRouter(
            providers=[gemini, groq],
            default_provider=provider_name,
            allow_fallback=False,
        )

    return ProviderRouter(
        providers=[groq, gemini],
        default_provider=None,
        allow_fallback=True,
    )


def _fmt_args(arguments: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in (arguments or {}).items())


class AgentREPL:
    """Interactive Gemini-CLI-style agent REPL for a single session.

    Pass a ``client`` (AtlasClient) or a ``client_factory``.  ``confirm`` may be
    injected for tests; the default gates WRITE tools via ``click.confirm``.
    """

    def __init__(
        self,
        *,
        provider: Any,
        client: Any = None,
        client_factory: Callable[[], Any] | None = None,
        registry: ToolRegistry | None = None,
        confirm: Callable[[str, dict], bool] | None = None,
        now: Callable[[], datetime] | None = None,
        echo: Callable[[str], None] = click.echo,
    ) -> None:
        self.provider = provider
        self.registry = registry or ToolRegistry()
        self._client = client
        self._client_factory = client_factory
        self._confirm = confirm
        self._now = now or (lambda: datetime.now(UTC))
        self._echo = echo
        self._history: list[tuple[str, str]] = []

    def _build_client(self) -> Any:
        if self._client is not None:
            return self._client
        if self._client_factory is not None:
            self._client = self._client_factory()
            return self._client
        raise RuntimeError("AgentREPL requires a client or client_factory")

    def _prompt_confirm(self, tool_name: str, arguments: dict) -> bool:
        return click.confirm(
            f"Allow {tool_name}({_fmt_args(arguments)})?", default=False
        )

    def _render_progress(self, call: Any, obs: Any) -> None:
        ok = obs is not None and bool(getattr(obs, "success", False))
        marker = _PROGRESS_OK if ok else _PROGRESS_FAIL
        self._echo(f"  {marker} {call.tool_name}")

    def run_turn(self, user_text: str) -> str:
        """Run the agent loop for one user turn; returns the assistant reply."""
        loop = AgentLoop(
            provider=self.provider,
            registry=self.registry,
            client=self._build_client(),
            confirm=self._confirm or self._prompt_confirm,
            on_tool=self._render_progress,
            conversation_history=self._history,
            now=self._now,
        )
        result = loop.run(user_text)
        if result.ok:
            reply = result.response or "Done."
        elif result.needs_clarification:
            reply = result.response or "I need more information to answer that."
        else:
            reply = (
                result.error
                or result.response
                or "I couldn't complete that request."
            )
        self._history.append((user_text, reply))
        return reply

    def interact(self) -> int:
        """Run the interactive read/respond loop until Ctrl-C or EOF.

        Returns the process exit code (0 for a clean exit).
        """
        self._echo("Atlas agent — type a question, or Ctrl-C/^D to exit.")
        while True:
            try:
                raw = input("You > ")
            except (EOFError, KeyboardInterrupt):
                self._echo("")
                break
            line = (raw or "").strip()
            if not line:
                continue
            if line.lower() in _STOP_COMMANDS:
                break
            try:
                reply = self.run_turn(line)
            except KeyboardInterrupt:
                self._echo("(interrupted)")
                break
            self._echo(f"Atlas > {reply}")
            self._echo("")
        return ExitCode.SUCCESS


def run_one_shot(
    task: str,
    *,
    provider: Any,
    client: Any,
    registry: ToolRegistry | None = None,
    echo: Callable[[str], None] = click.echo,
) -> int:
    """Run the agent loop once (non-interactive, auto-approve) over ``task``.

    Returns the process exit code.  The brain-unavailable case is NOT handled
    here (the caller refuses to start with exit 10 before invoking this);
    unrelated agent failures map to ``ExitCode.UNSPECIFIED``.
    """
    loop = AgentLoop(
        provider=provider,
        registry=registry or ToolRegistry(),
        client=client,
    )
    result = loop.run(task)
    if result.ok:
        echo(result.response or "Done.")
        return ExitCode.SUCCESS
    if result.needs_clarification:
        echo(result.response or "I need more information to answer that.")
        return ExitCode.SUCCESS
    echo(f"error: {result.error or 'agent could not complete the task'}")
    return ExitCode.UNSPECIFIED
