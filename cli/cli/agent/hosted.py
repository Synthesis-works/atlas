"""Hosted conversational agent UX (P2) — server brain via the P1 session API.

``atlas`` (interactive TTY) and ``atlas "natural language"`` (one-shot) drive
the *hosted* Atlas agent through the authenticated session endpoints exposed by
P1.  The server owns provider credentials; the CLI never sees a provider key.

Every turn is processed through the P1 lifecycle state machine:

- ``READY`` — turn finished; print the reply.
- ``RUNNING`` / ``WAITING_FOR_EXECUTION`` — poll ``GET /sessions/{id}`` until
  the server settles the turn.
- ``AWAITING_APPROVAL`` — surface the pending tool; only approve after an
  explicit user confirmation (never auto-approve).  Refusing cancels the turn.
- ``AWAITING_CLARIFICATION`` — surface the question; in the interactive REPL
  accept an answer and continue, otherwise stop with the question printed.

The BYOK local-loop agent (``atlas agent ...``) is intentionally untouched.
"""

from __future__ import annotations

import contextlib
import sys
import time
import typing as t
from collections.abc import Callable

import click

from cli.errors import ExitCode


class AgentSessionClient(t.Protocol):
    """Minimal session-API surface the hosted UX requires (duck-typed).

    Mirrors the ``AtlasClient`` session methods from P1; tests substitute a
    scripted stand-in, so the protocol deliberately returns ``Any`` objects.
    """

    def create_agent_session(self, goal: str, provider: str | None) -> t.Any: ...
    def send_agent_session_message(self, session_id: str, message: str) -> t.Any: ...
    def get_agent_session(self, session_id: str) -> t.Any: ...
    def approve_agent_session(self, session_id: str, approval_token: str) -> t.Any: ...
    def clarify_agent_session(self, session_id: str, answer: str) -> t.Any: ...
    def cancel_agent_session(self, session_id: str) -> t.Any: ...
    def delete_agent_session(self, session_id: str) -> None: ...


#: Server-side hosted brain; the CLI never needs a provider key for this.
HOSTED_PROVIDER = "gemini"
#: Poll interval when a turn runs asynchronously on the server.
POLL_INTERVAL = 1.0

_STOP_COMMANDS = {"exit", "quit", "q"}

# States mirrored from the sessions router (P1).
_READY = "READY"
_RUNNING = "RUNNING"
_AWAITING_APPROVAL = "AWAITING_APPROVAL"
_AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
_WAITING_FOR_EXECUTION = "WAITING_FOR_EXECUTION"

_GREETING = "Atlas: Hi! I'm Atlas. What would you like to work on?"


def _final_reply(session: t.Any, reply: str | None) -> str:
    """Best available reply for a finished turn.

    The server syncs an assistant transcript message exactly once per task on
    every read, so the transcript tail is the authoritative final reply.  The
    per-step ``reply`` (from a message/approve/clarify response) can be stale
    when a turn resumed from an intermediate state before finishing.
    """
    for message in reversed(getattr(session, "transcript", None) or []):
        if getattr(message, "role", None) == "assistant" and getattr(message, "content", None):
            return message.content
    if reply:
        return reply
    return "Done."


def _approval_prompt(tool_name: str | None) -> bool:
    who = tool_name or "this tool"
    return click.confirm(f"Atlas needs your approval for {who}. Approve?", default=False)


class HostedSessionTurn:
    """Processes a hosted session turn until it finishes or needs the user."""

    def __init__(
        self,
        client: AgentSessionClient,
        *,
        confirm: Callable[[str | None], bool] | None = None,
        sleep: Callable[[float], None] | None = None,
        echo: Callable[[str], None] = click.echo,
    ) -> None:
        self.client = client
        self._confirm = confirm or _approval_prompt
        self._sleep = sleep or time.sleep
        self._echo = echo

    def process(
        self,
        session_id: str,
        session: t.Any,
        *,
        reply: str | None = None,
        interactive: bool,
    ) -> tuple[t.Any, str | None]:
        """Drive the turn to a terminal state.

        Returns ``(final_session, reply)``.  ``reply`` is ``None`` when the
        turn could not complete (blocked on clarification and not
        interactive, or an unknown state).
        """
        state = getattr(session, "state", None)
        while state not in (_READY, None):
            if state in (_RUNNING, _WAITING_FOR_EXECUTION):
                self._sleep(POLL_INTERVAL)
                session = self.client.get_agent_session(session_id)
                state = getattr(session, "state", None)
                continue

            if state == _AWAITING_APPROVAL:
                pending = getattr(session, "pending_action", None)
                tool_name = getattr(pending, "tool_name", None) if pending else None
                token = getattr(pending, "approval_token", None) if pending else None
                if interactive and self._confirm(tool_name):
                    if not token:
                        self._echo("error: approval is pending but no approval token was returned.")
                        return session, None
                    resumed = self.client.approve_agent_session(session_id, approval_token=token)
                    session = resumed.session
                    reply = resumed.reply
                else:
                    cancelled = self.client.cancel_agent_session(session_id)
                    self._echo("Declined — turn cancelled.")
                    return cancelled.session, cancelled.reply
                state = getattr(session, "state", None)
                continue

            if state == _AWAITING_CLARIFICATION:
                pending = getattr(session, "pending_action", None)
                question = getattr(pending, "question", None) if pending else None
                if not interactive:
                    self._echo(question or "I need more information to answer that.")
                    return session, None
                self._echo(f"Atlas: {question or 'I need more information to answer that.'}")
                answer = input("Atlas > ").strip()
                if not answer:
                    self._echo("Declined — turn cancelled.")
                    cancelled = self.client.cancel_agent_session(session_id)
                    return cancelled.session, cancelled.reply
                resumed = self.client.clarify_agent_session(session_id, answer=answer)
                session = resumed.session
                reply = resumed.reply
                state = getattr(session, "state", None)
                continue

            self._echo(f"error: unexpected session state '{state}'.")
            return session, None

        return session, _final_reply(session, reply)


class HostedAgentREPL:
    """Interactive hosted-agent REPL for one conversation.

    The session is created lazily with the first user message (P1's create
    endpoint runs the first turn from ``goal``), so no wasted or blocking
    "intro" turn is ever executed server-side.
    """

    def __init__(
        self,
        client: AgentSessionClient,
        *,
        echo: Callable[[str], None] = click.echo,
        confirm: Callable[[str | None], bool] | None = None,
        sleep: Callable[[float], None] | None = None,
        delete_session_on_exit: bool = True,
    ) -> None:
        self.client = client
        self._echo = echo
        self._delete_on_exit = delete_session_on_exit
        self._turn = HostedSessionTurn(client, confirm=confirm, sleep=sleep, echo=echo)
        self._session_id: str | None = None

    def interact(self) -> int:
        """Loop user turns until EOF / Ctrl-C / quit."""
        self._echo(_GREETING)
        self._echo("")

        exit_code = ExitCode.SUCCESS
        while True:
            try:
                raw = input("Atlas > ")
            except (EOFError, KeyboardInterrupt):
                self._echo("")
                self._echo("Bye!")
                break
            line = (raw or "").strip()
            if not line:
                continue
            if line.lower() in _STOP_COMMANDS:
                self._echo("Bye!")
                break
            try:
                self._run_turn(line)
            except KeyboardInterrupt:
                self._echo("(interrupted)")
                exit_code = ExitCode.INTERRUPTED
                break
        self._cleanup()
        return exit_code

    def _run_turn(self, line: str) -> None:
        if self._session_id is None:
            session = self.client.create_agent_session(line, provider=HOSTED_PROVIDER)
            self._session_id = session.session_id
            turn_session = session
            turn_reply = None
        else:
            turned = self.client.send_agent_session_message(self._session_id, message=line)
            turn_session = turned.session
            turn_reply = turned.reply
        _, reply = self._turn.process(
            self._session_id or turn_session.session_id,
            turn_session,
            reply=turn_reply,
            interactive=True,
        )
        self._echo(f"Atlas: {reply or 'Done.'}")
        self._echo("")

    def _cleanup(self) -> None:
        if self._delete_on_exit and self._session_id is not None:
            with contextlib.suppress(Exception):
                self.client.delete_agent_session(self._session_id)


def run_hosted_one_shot(
    client: AgentSessionClient,
    task: str,
    *,
    echo: Callable[[str], None] = click.echo,
    confirm: Callable[[str | None], bool] | None = None,
    sleep: Callable[[float], None] | None = None,
    interactive: bool | None = None,
) -> int:
    """Run ``atlas "task"``: create a session, run the turn, print the result.

    P1's create endpoint runs the first turn from ``goal``, so no extra
    message is sent.  Approvals are only honored after explicit user
    confirmation; a blocked turn (clarification without an interactive
    terminal, or an approval declined) exits without executing.
    """
    if interactive is None:
        interactive = _is_tty()
    session = client.create_agent_session(task, provider=HOSTED_PROVIDER)
    try:
        _, reply = HostedSessionTurn(client, confirm=confirm, sleep=sleep, echo=echo).process(
            session.session_id,
            session,
            reply=None,
            interactive=interactive,
        )
        if reply is None:
            echo("")
            echo("The request is waiting for your input. Run `atlas` to continue it interactively.")
            return ExitCode.SUCCESS
        echo("")
        echo(f"Atlas: {reply}")
        return ExitCode.SUCCESS
    finally:
        with contextlib.suppress(Exception):
            client.delete_agent_session(session.session_id)


def _is_tty() -> bool:
    try:
        return bool(sys.stdin.isatty())
    except Exception:  # noqa: BLE001
        return False
