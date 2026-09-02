"""Tests for the CLI agent REPL + one-shot surface (Phase 4).

Covers: the one-shot runner's exit codes, the interactive REPL's turn handling
with session history, WRITE-tool confirmation gating (approve vs reject, read
tools never prompting), command routing (bare ``atlas`` → help when non-TTY;
``atlas agent`` → exit 10 when brain unavailable), and the new exit code.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from click.testing import CliRunner

from cli.agent.loop import AgentLoop
from cli.agent.repl import AgentREPL, _progress_glyphs, build_agent_provider, run_one_shot
from cli.agent.state import AgentDecision, AgentDecisionType
from cli.agent.tools.registry import ToolRegistry
from cli.app import main
from cli.errors import ExitCode


def _id(n: int = 1) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-0000-0000-00000000000{n}")


class FakeProvider:
    """Scripted provider returning queued decisions."""

    def __init__(self, decisions: list[AgentDecision]) -> None:
        self._decisions = list(decisions)
        self.contexts: list[str] = []

    def decide(self, task: str, prompt_context: str, available_tools: list[dict]) -> AgentDecision:
        self.contexts.append(prompt_context)
        if not self._decisions:
            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE, response="done"
            )
        return self._decisions.pop(0)


def _tool(name: str, **args: Any) -> AgentDecision:
    return AgentDecision(
        type=AgentDecisionType.TOOL_CALL, tool_name=name, arguments=args
    )


def _final(text: str) -> AgentDecision:
    return AgentDecision(type=AgentDecisionType.FINAL_RESPONSE, response=text)


def _fail(msg: str) -> AgentDecision:
    return AgentDecision(type=AgentDecisionType.FAIL, error_message=msg)


class MockClient:
    """AtlasClient-shaped stub for the tools exercised here."""

    def __init__(self) -> None:
        from atlas_sdk.models.benchmarks import BenchmarkRead, PageResponse
        from atlas_sdk.models.executions import ExecutionResponse

        self.submit_executed = False
        self.list_executed = 0

        def _list(limit=50):
            self.list_executed += 1
            return PageResponse(
                items=[
                    BenchmarkRead(
                        id=_id(1), project_id=_id(9), name="B1", state="published"
                    )
                ],
                total=1, limit=limit, offset=0,
            )

        self.list_benchmarks = _list
        self.submit_execution = (
            lambda bv_id, target_model="mock", dataset_version_id=None: (
                self._mark_submit(),
                ExecutionResponse(
                    id=_id(4), benchmark_version_id=uuid.UUID(str(bv_id)),
                    status="QUEUED", target_model=target_model,
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    updated_at=datetime(2026, 1, 1, tzinfo=UTC),
                    created_by=_id(9),
                ),
            )[1]
        )

    def _mark_submit(self) -> None:
        self.submit_executed = True


class TestConfirmGating:
    def test_approve_executes_write_tool(self) -> None:
        client = MockClient()
        provider = FakeProvider(
            [_tool("submit_run", benchmark_version_id=str(_id(2)), target_model="mock"),
             _final("queued")]
        )
        loop = AgentLoop(
            provider=provider,  # type: ignore[arg-type]
            registry=ToolRegistry(),
            client=client,  # type: ignore[arg-type]
            confirm=lambda tool, args: True,
        )
        result = loop.run("submit a run")
        assert result.ok is True
        assert client.submit_executed is True
        assert loop.context.observations[-1].success is True
        assert loop.context.observations[-1].error is None

    def test_reject_skips_execution_and_records_declined(self) -> None:
        client = MockClient()
        provider = FakeProvider(
            [_tool("submit_run", benchmark_version_id=str(_id(2)), target_model="mock"),
             _final("ok, skipped")]
        )
        loop = AgentLoop(
            provider=provider,  # type: ignore[arg-type]
            registry=ToolRegistry(),
            client=client,  # type: ignore[arg-type]
            confirm=lambda tool, args: False,
        )
        result = loop.run("submit a run")
        assert result.ok is True
        assert client.submit_executed is False
        obs = loop.context.observations[0]
        assert obs.success is False
        assert obs.error == "mutation declined by user"

    def test_read_tool_never_prompts(self) -> None:
        client = MockClient()
        calls: list[tuple[str, dict]] = []

        def confirm(tool: str, args: dict) -> bool:
            calls.append((tool, args))
            return True

        provider = FakeProvider([_tool("list_benchmarks"), _final("listed")])
        loop = AgentLoop(
            provider=provider,  # type: ignore[arg-type]
            registry=ToolRegistry(),
            client=client,  # type: ignore[arg-type]
            confirm=confirm,
        )
        result = loop.run("list")
        assert result.ok is True
        assert calls == []  # READ tool never prompted
        assert client.list_executed == 1  # but the read tool did run

    def test_default_auto_approves_when_confirm_none(self) -> None:
        client = MockClient()
        provider = FakeProvider(
            [_tool("submit_run", benchmark_version_id=str(_id(2)), target_model="mock"),
             _final("queued")]
        )
        loop = AgentLoop(
            provider=provider,  # type: ignore[arg-type]
            registry=ToolRegistry(),
            client=client,  # type: ignore[arg-type]
            confirm=None,
        )
        result = loop.run("submit")
        assert result.ok is True
        assert client.submit_executed is True


class TestRunOneShot:
    def test_final_response_returns_success(self) -> None:
        out: list[str] = []
        code = run_one_shot(
            "task", provider=FakeProvider([_final("answer")]),
            client=MockClient(), echo=out.append,
        )
        assert code == ExitCode.SUCCESS
        assert out == ["answer"]

    def test_fail_returns_unspecified(self) -> None:
        out: list[str] = []
        code = run_one_shot(
            "task", provider=FakeProvider([_fail("bad")]),
            client=MockClient(), echo=out.append,
        )
        assert code == ExitCode.UNSPECIFIED

    def test_clarification_returns_success(self) -> None:
        code = run_one_shot(
            "task",
            provider=FakeProvider(
                [AgentDecision(type=AgentDecisionType.REQUEST_CLARIFICATION, response="Which?")]
            ),
            client=MockClient(), echo=lambda s: None,
        )
        assert code == ExitCode.SUCCESS


class TestAgentREPLTurn:
    def test_turn_returns_reply_and_records_history(self) -> None:
        repl = AgentREPL(
            provider=FakeProvider([_final("hello!")]),
            client=MockClient(),
            echo=lambda s: None,
        )
        reply = repl.run_turn("hi")
        assert reply == "hello!"
        assert repl._history == [("hi", "hello!")]

    def test_history_is_passed_to_provider(self) -> None:
        provider = FakeProvider([_final("x")])
        repl = AgentREPL(provider=provider, client=MockClient(), echo=lambda s: None)
        repl.run_turn("first")
        repl.run_turn("second")
        # on the second turn the transcript should include prior history
        assert "first" in provider.contexts[-1]

    def test_confirm_approve_in_repl(self) -> None:
        client = MockClient()
        repl = AgentREPL(
            provider=FakeProvider(
                [_tool("submit_run", benchmark_version_id=str(_id(2)), target_model="mock"),
                 _final("queued")]
            ),
            client=client,
            confirm=lambda tool, args: True,
            echo=lambda s: None,
        )
        repl.run_turn("submit")
        assert client.submit_executed is True

    def test_confirm_reject_in_repl(self) -> None:
        client = MockClient()
        repl = AgentREPL(
            provider=FakeProvider(
                [_tool("submit_run", benchmark_version_id=str(_id(2)), target_model="mock"),
                 _final("ok skipped")]
            ),
            client=client,
            confirm=lambda tool, args: False,
            echo=lambda s: None,
        )
        repl.run_turn("submit")
        assert client.submit_executed is False


class TestExitCode:
    def test_agent_unavailable_is_10(self) -> None:
        assert ExitCode.AGENT_UNAVAILABLE == 10


class TestRouting:
    def test_bare_atlas_non_tty_shows_help(
        self, runner: CliRunner
    ) -> None:
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Atlas CLI" in result.output

    def test_agent_command_without_key_exits_10(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        result = runner.invoke(main, ["agent", "list benchmarks"])
        assert result.exit_code == ExitCode.AGENT_UNAVAILABLE
        assert "GEMINI_API_KEY" in result.output

    def test_agent_appears_in_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "agent" in result.output

    def test_bare_atlas_tty_enters_repl(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setattr("cli.app._is_tty", lambda: True)
        # stub _run_repl so we isolate the routing decision (its real behavior is
        # covered by the direct _run_repl test below)
        monkeypatch.setattr("cli.app._run_repl", lambda ctx: ExitCode.AGENT_UNAVAILABLE)
        result = runner.invoke(main, [])
        assert result.exit_code == ExitCode.AGENT_UNAVAILABLE

    def test_run_repl_without_key_returns_10(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cli.app import Context, _run_repl

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        ctx = Context()
        assert _run_repl(ctx) == ExitCode.AGENT_UNAVAILABLE


class TestProviderAvailability:
    def test_build_agent_provider_unavailable_without_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        provider = build_agent_provider()
        assert provider.available is False

    def test_build_agent_provider_available_with_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        provider = build_agent_provider()
        assert provider.available is True


class TestProgressGlyphs:
    def test_cp1252_falls_back_to_ascii(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class Cp1252:
            encoding = "cp1252"

        monkeypatch.setattr("cli.agent.repl.sys.stdout", Cp1252())
        ok, fail = _progress_glyphs()
        assert ok == "[ok]"
        assert fail == "[!]"

    def test_utf8_uses_unicode_glyphs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class Utf8:
            encoding = "utf-8"

        monkeypatch.setattr("cli.agent.repl.sys.stdout", Utf8())
        ok, fail = _progress_glyphs()
        assert ok == "\u2713"
        assert fail == "\u2717"


class TestInteract:
    def test_eof_exits_cleanly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def raiser(*_a, **_k):
            raise EOFError

        monkeypatch.setattr("builtins.input", raiser)
        repl = AgentREPL(provider=FakeProvider([]), client=MockClient(), echo=print)
        assert repl.interact() == ExitCode.SUCCESS

    def test_keyboard_interrupt_exits_cleanly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def raiser(*_a, **_k):
            raise KeyboardInterrupt

        monkeypatch.setattr("builtins.input", raiser)
        repl = AgentREPL(provider=FakeProvider([]), client=MockClient(), echo=print)
        assert repl.interact() == ExitCode.SUCCESS
