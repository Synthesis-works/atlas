"""Tests for the hosted conversational agent UX (P2).

Covers agent-first routing (bare ``atlas`` TTY REPL, non-TTY help, one-shot
``atlas "NL"``), known-command precedence, ``atlas agent`` BYOK unaffectedness,
hosted-before-BYOUK preference, the no-auth/no-key guidance + exit 10, session
reuse across REPL turns, server polling, approval (explicit-only) and
clarification flows, and hidden ``_nlu``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from cli.agent.hosted import HostedAgentREPL, run_hosted_one_shot
from cli.app import main
from cli.errors import ExitCode


def _msg(role: str, content: str) -> SimpleNamespace:
    return SimpleNamespace(role=role, content=content)


def _pend(
    *,
    action: str | None = "approve",
    tool_name: str | None = None,
    approval_token: str | None = None,
    question: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        action=action,
        tool_name=tool_name,
        approval_token=approval_token,
        question=question,
    )


def _session(
    sid: str = "s1",
    state: str = "READY",
    transcript: list[SimpleNamespace] | None = None,
    pending_action: SimpleNamespace | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        session_id=sid,
        state=state,
        transcript=transcript or [],
        pending_action=pending_action,
    )


def _turn(session: SimpleNamespace, reply: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(session=session, reply=reply)


def _inputs(values: list[str]) -> object:
    """Input() factory: yields values then raises EOFError (clean REPL exit)."""
    it = iter(values)

    def _input(_prompt: str = "") -> str:
        try:
            return next(it)
        except StopIteration:
            raise EOFError from None

    return _input


_ANY_PROVIDER = object()  # sentinel for the BYOK provider argument in tests


class FakeClient:
    """Scriptable, duck-typed stand-in for the AtlasClient session surface."""

    def __init__(self, **handlers: object) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.deleted: list[str] = []
        self._handlers = handlers

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def _invoke(self, name: str, args: tuple, kwargs: dict) -> object:
        self.calls.append((name, args, kwargs))
        handler = self._handlers.get(name)
        if handler is not None:
            return handler(*args, **kwargs)
        if name == "delete_agent_session":
            self.deleted.append(args[0])
            return None
        raise AssertionError(f"FakeClient: unhandled call {name}({args}, {kwargs})")

    def create_agent_session(self, goal: str, provider: str | None = None) -> object:
        return self._invoke("create_agent_session", (goal,), {"provider": provider})

    def send_agent_session_message(self, session_id: str, message: str) -> object:
        return self._invoke("send_agent_session_message", (session_id,), {"message": message})

    def get_agent_session(self, session_id: str) -> object:
        return self._invoke("get_agent_session", (session_id,), {})

    def approve_agent_session(self, session_id: str, approval_token: str) -> object:
        return self._invoke(
            "approve_agent_session", (session_id,), {"approval_token": approval_token}
        )

    def clarify_agent_session(self, session_id: str, answer: str) -> object:
        return self._invoke("clarify_agent_session", (session_id,), {"answer": answer})

    def cancel_agent_session(self, session_id: str) -> object:
        return self._invoke("cancel_agent_session", (session_id,), {})

    def delete_agent_session(self, session_id: str) -> None:
        self._invoke("delete_agent_session", (session_id,), {})


@pytest.fixture
def token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_TOKEN", "tok-abc")


def _patch_build_client(monkeypatch: pytest.MonkeyPatch, client: FakeClient) -> None:
    monkeypatch.setattr("cli.client.build_client", lambda cfg: client)
    monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)


class TestRouting:
    def test_oneshot_routes_through_hidden_nlu(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, token: None
    ) -> None:
        _ = token
        out: list[str] = []
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: (
                out.append(f"create:{goal}:{provider}"),
                _session(transcript=[_msg("assistant", "Consider it done.")]),
            )[1],
            delete_agent_session=lambda sid: out.append(f"delete:{sid}"),
        )
        _patch_build_client(monkeypatch, client)
        result = runner.invoke(main, ["list benchmarks"])
        assert result.exit_code == 0
        assert "Atlas: Consider it done." in result.output
        assert out == ["create:list benchmarks:gemini", "delete:s1"]

    def test_command_precedence_known_command_wins(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, token: None
    ) -> None:
        _ = token
        calls: list[str] = []

        def _tracer(_cfg: object) -> FakeClient:
            calls.append("build_client")
            client = FakeClient(
                create_agent_session=lambda goal, provider=None: (_ for _ in ()).throw(
                    AssertionError("hosted NL was used for a known command")
                )
            )
            return client

        monkeypatch.setattr("cli.client.build_client", _tracer)
        result = runner.invoke(main, ["logout"])
        assert result.exit_code == 0
        assert "Logged out" in result.output
        assert calls == []  # a known command must never build the hosted client

    def test_agent_command_uses_byok_not_hosted(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, token: None
    ) -> None:
        _ = token
        ran: list[str] = []

        class FakeProvider:
            available = True

        monkeypatch.setattr(
            "cli.agent.repl.build_agent_provider", lambda provider_name="auto": FakeProvider()
        )
        monkeypatch.setattr(
            "cli.agent.repl.run_one_shot",
            lambda task, provider=_ANY_PROVIDER, client=None: (
                ran.append(task),
                ExitCode.SUCCESS,
            )[1],
        )
        fake = FakeClient()
        monkeypatch.setattr("cli.client.build_client", lambda cfg: fake)
        result = runner.invoke(main, ["agent", "list benchmarks"])
        assert result.exit_code == 0
        assert ran == ["list benchmarks"]
        assert fake.calls == []  # the BYOK path never touches the hosted session API

    def test_nlu_hidden_from_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "_nlu" not in result.output

    def test_unknown_command_routes_to_hosted_oneshot(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, token: None
    ) -> None:
        _ = token
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                transcript=[_msg("assistant", "I found no such command, but here is what I know.")]
            )
        )
        _patch_build_client(monkeypatch, client)
        result = runner.invoke(main, ["nonexistent"])
        assert result.exit_code == 0
        assert "I found no such command" in result.output
        assert "create_agent_session" in [c[0] for c in client.calls]

    def test_command_name_first_word_never_becomes_nlu(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, token: None
    ) -> None:
        # ``run`` is a registered command, so a free-form phrase that STARTS
        # with a command name must resolve as that command (its own usage
        # error here), never leak into the hosted NLU path.
        _ = token
        client = FakeClient()
        _patch_build_client(monkeypatch, client)
        result = runner.invoke(main, ["run", "the", "mock", "suite"])
        assert result.exit_code == 2  # run group: no such subcommand 'the'
        assert client.calls == []  # hosted session API was never touched

    def test_no_auth_no_key_bare_atlas_guidance_exit_10(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("cli.app._is_tty", lambda: True)
        result = runner.invoke(main, [])
        assert result.exit_code == ExitCode.AGENT_UNAVAILABLE
        assert "atlas login" in result.output

    def test_no_auth_oneshot_guidance_exit_10(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["do stuff"])
        assert result.exit_code == ExitCode.AGENT_UNAVAILABLE
        assert "atlas login" in result.output


class TestOneshot:
    def test_creates_sends_nothing_and_archives_readily(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                transcript=[_msg("assistant", "done")]
            )
        )
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        out: list[str] = []
        code = run_hosted_one_shot(client, "task", echo=out.append, interactive=False)
        assert code == ExitCode.SUCCESS
        assert out == ["", "Atlas: done"]
        assert client.calls[0][0] == "create_agent_session"
        assert client.calls[0][1][0] == "task"
        assert client.calls[-1][0] == "delete_agent_session"

    def test_polls_running_turn_until_ready(self, monkeypatch: pytest.MonkeyPatch) -> None:
        read_count = [0]

        def get(sid: str) -> object:
            read_count[0] += 1
            if read_count[0] < 2:
                return _session(state="RUNNING")
            return _session(state="READY", transcript=[_msg("assistant", "finally")])

        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(state="RUNNING"),
            get_agent_session=get,
        )
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        out: list[str] = []
        code = run_hosted_one_shot(client, "task", echo=out.append, interactive=False)
        assert code == ExitCode.SUCCESS
        assert out[-1] == "Atlas: finally"
        assert read_count[0] == 2

    def test_approves_only_after_explicit_confirm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pend = _pend(tool_name="create_benchmark", approval_token="tok-1")
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="AWAITING_APPROVAL", pending_action=pend
            ),
            approve_agent_session=lambda sid, approval_token=None: _turn(
                _session(state="READY", transcript=[_msg("assistant", "approved and done")])
            ),
        )
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        confirms: list[str | None] = []
        out: list[str] = []
        code = run_hosted_one_shot(
            client,
            "task",
            echo=out.append,
            confirm=lambda tool: (confirms.append(tool), True)[1],
            interactive=True,
        )
        assert code == ExitCode.SUCCESS
        assert confirms == ["create_benchmark"]
        approve_call = [c for c in client.calls if c[0] == "approve_agent_session"]
        assert len(approve_call) == 1
        assert approve_call[0][2]["approval_token"] == "tok-1"
        assert out[-1] == "Atlas: approved and done"

    def test_approve_resume_returns_final_transcript_not_intermediate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # After approving, the turn resumes through RUNNING; the final printed
        # answer must be the server-synced completion transcript tail, NOT the
        # intermediate "requires approval" reply from the approve response.
        pend = _pend(tool_name="submit_run", approval_token="tok-1")
        approve_turn = _turn(
            _session(
                state="RUNNING",
                transcript=[_msg("assistant", "running with approval granted")],
            ),
            reply="running with approval granted",
        )
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="AWAITING_APPROVAL",
                pending_action=pend,
                transcript=[_msg("assistant", "Tool submit_run requires your approval")],
            ),
            approve_agent_session=lambda sid, approval_token=None: approve_turn,
            get_agent_session=lambda sid: _session(
                state="READY",
                transcript=[
                    _msg("assistant", "Tool submit_run requires your approval"),
                    _msg("assistant", "all done"),
                ],
            ),
        )
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        out: list[str] = []
        code = run_hosted_one_shot(
            client, "task", echo=out.append, confirm=lambda _t: True, interactive=True
        )
        assert code == ExitCode.SUCCESS
        assert out[-1] == "Atlas: all done"

    def test_declined_approval_cancels_safely(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="AWAITING_APPROVAL",
                pending_action=_pend(tool_name="create_benchmark", approval_token="tok-1"),
            ),
            cancel_agent_session=lambda sid: _turn(_session(), reply="Task cancelled."),
        )
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        out: list[str] = []
        code = run_hosted_one_shot(
            client, "task", echo=out.append, confirm=lambda _t: False, interactive=True
        )
        assert code == ExitCode.SUCCESS
        assert "Declined" in "\n".join(out)
        call_names = [c[0] for c in client.calls]
        assert "cancel_agent_session" in call_names
        assert "approve_agent_session" not in call_names

    def test_nontty_one_shot_never_auto_approves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        confirm_called: list[str] = []
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="AWAITING_APPROVAL",
                pending_action=_pend(tool_name="write_file", approval_token="tok-1"),
            ),
            cancel_agent_session=lambda sid: _turn(_session(), reply="cancelled"),
        )
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        out: list[str] = []
        code = run_hosted_one_shot(
            client,
            "task",
            echo=out.append,
            confirm=lambda tool: (confirm_called.append(tool), True)[1],
            interactive=False,
        )
        assert code == ExitCode.SUCCESS
        assert confirm_called == []  # no prompt in automation, no auto-approval
        assert "approve_agent_session" not in [c[0] for c in client.calls]

    def test_clarification_interactive_asks_and_continues(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pend = _pend(action="clarify", question="Which model?")
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="AWAITING_CLARIFICATION", pending_action=pend
            ),
            clarify_agent_session=lambda sid, answer="": _turn(
                _session(state="READY", transcript=[_msg("assistant", "ran on mock")])
            ),
        )
        monkeypatch.setattr("builtins.input", _inputs(["mock"]))
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        out: list[str] = []
        code = run_hosted_one_shot(client, "task", echo=out.append, interactive=True)
        assert code == ExitCode.SUCCESS
        assert "Which model?" in "\n".join(out)
        clarify = [c for c in client.calls if c[0] == "clarify_agent_session"]
        assert clarify[0][2]["answer"] == "mock"
        assert out[-1] == "Atlas: ran on mock"

    def test_clarification_nontty_prints_guidance_and_stops(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="AWAITING_CLARIFICATION",
                pending_action=_pend(action="clarify", question="Which model?"),
            ),
        )
        monkeypatch.setattr("builtins.input", _inputs(["mock"]))
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        out: list[str] = []
        code = run_hosted_one_shot(client, "task", echo=out.append, interactive=False)
        assert code == ExitCode.SUCCESS
        joined = "\n".join(out)
        assert "Which model?" in joined
        assert "continue it interactively" in joined
        assert "clarify_agent_session" not in [c[0] for c in client.calls]


class TestRepl:
    def test_tty_repl_greets_and_runs_hosted_first_message(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, token: None
    ) -> None:
        _ = token
        monkeypatch.setattr("builtins.input", _inputs(["hello", "exit"]))
        monkeypatch.setattr("cli.app._is_tty", lambda: True)
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="READY", transcript=[_msg("assistant", "hi there")]
            )
        )
        _patch_build_client(monkeypatch, client)
        result = runner.invoke(main, [])
        assert result.exit_code == ExitCode.SUCCESS
        assert "Atlas: Hi! I'm Atlas." in result.output
        assert "Atlas: hi there" in result.output
        assert client.calls[0][0] == "create_agent_session"
        assert client.calls[0][1][0] == "hello"
        assert client.deleted == ["s1"]

    def test_repl_reuses_one_session_across_turns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="READY", transcript=[_msg("assistant", "first reply")]
            ),
            send_agent_session_message=lambda sid, message="": _turn(
                _session(transcript=[_msg("assistant", "second reply")])
            ),
        )
        monkeypatch.setattr("builtins.input", _inputs(["first", "second", "exit"]))
        repl = HostedAgentREPL(client, sleep=lambda _s: None)
        code = repl.interact()
        assert code == ExitCode.SUCCESS
        creates = [c for c in client.calls if c[0] == "create_agent_session"]
        sends = [c for c in client.calls if c[0] == "send_agent_session_message"]
        assert len(creates) == 1
        assert creates[0][1][0] == "first"
        assert len(sends) == 1
        assert sends[0][2]["message"] == "second"
        assert client.deleted == ["s1"]

    def test_eof_at_clarification_archives_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """EOF raised at the *nested* clarification prompt still archives the session."""
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="AWAITING_CLARIFICATION",
                pending_action=_pend(action="clarify", question="Which model?"),
            )
        )

        def _inputs_then_eof() -> object:
            it = iter(["hello"])

            def _input(_prompt: str = "") -> str:
                try:
                    return next(it)
                except StopIteration:
                    raise EOFError from None

            return _input

        monkeypatch.setattr("builtins.input", _inputs_then_eof())
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        out: list[str] = []
        repl = HostedAgentREPL(client, sleep=lambda _s: None, echo=out.append)
        code = repl.interact()
        assert code == ExitCode.SUCCESS
        assert "Bye!" in "\n".join(out)
        assert client.deleted == ["s1"]

    def test_ctrl_c_at_clarification_archives_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ctrl-C raised at the *nested* clarification prompt still archives the session."""
        client = FakeClient(
            create_agent_session=lambda goal, provider=None: _session(
                state="AWAITING_CLARIFICATION",
                pending_action=_pend(action="clarify", question="Which model?"),
            )
        )

        def _inputs_then_interrupt() -> object:
            it = iter(["hello"])

            def _input(_prompt: str = "") -> str:
                try:
                    return next(it)
                except StopIteration:
                    raise KeyboardInterrupt from None

            return _input

        monkeypatch.setattr("builtins.input", _inputs_then_interrupt())
        monkeypatch.setattr("cli.agent.hosted.time.sleep", lambda _s: None)
        repl = HostedAgentREPL(client, sleep=lambda _s: None)
        code = repl.interact()
        assert code == ExitCode.INTERRUPTED
        assert client.deleted == ["s1"]


class TestProviderPreference:
    def test_hosted_wins_over_byok_when_authenticated(
        self, monkeypatch: pytest.MonkeyPatch, token: None
    ) -> None:
        _ = token

        def _boom(*_a: object, **_k: object) -> object:
            raise AssertionError("BYOK build_agent_provider must not run when authenticated")

        monkeypatch.setattr("cli.agent.repl.build_agent_provider", _boom)
        client = FakeClient(create_agent_session=lambda goal, provider=None: _session())
        monkeypatch.setattr("builtins.input", _inputs(["hello", "exit"]))
        monkeypatch.setattr("cli.client.build_client", lambda cfg: client)
        from cli.app import Context, _run_repl

        code = _run_repl(Context())
        assert code == ExitCode.SUCCESS
        assert client.calls[0][0] == "create_agent_session"
