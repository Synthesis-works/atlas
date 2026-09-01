"""Tests for the CLI agent loop (Phase 3).

The loop reads structured ``AgentDecision`` from the provider, dispatches tool
calls through the ``ToolRegistry`` (delegating to ``AtlasClient``), records
every tool call / observation in ``AgentContext``, and repeats until a final
response or a hard limit (steps / tool calls / deadline) is hit.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cli.agent.loop import AgentLoop, AgentResult
from cli.agent.prompt import build_context
from cli.agent.state import (
    AGENT_DEADLINE_SECONDS,
    MAX_AGENT_STEPS,
    MAX_AGENT_TOOL_CALLS,
    AgentContext,
    AgentDecision,
    AgentDecisionType,
    GoalExceededError,
)
from cli.agent.tools.registry import ToolRegistry


def _id(n: int) -> str:
    return f"00000000-0000-0000-0000-{n:012d}"


class FakeProvider:
    """Scripted provider: returns queued decisions, records context seen."""

    def __init__(self, decisions: list[AgentDecision]) -> None:
        self._decisions = list(decisions)
        self.contexts: list[str] = []

    def decide(self, task: str, prompt_context: str, available_tools: list[dict]) -> AgentDecision:
        self.contexts.append(prompt_context)
        if not self._decisions:
            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE, response="done (fallback)"
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


def _clarify(msg: str) -> AgentDecision:
    return AgentDecision(type=AgentDecisionType.REQUEST_CLARIFICATION, response=msg)


class MockAtlasClient:
    """Minimal AtlasClient-shaped stub returning SDK DTOs for the tools used."""

    def __init__(self) -> None:
        import uuid

        from atlas_sdk.models.benchmarks import BenchmarkRead, BenchmarkVersionRead, PageResponse
        from atlas_sdk.models.executions import ExecutionResponse
        from atlas_sdk.models.models import ModelRead, ModelStatus
        from atlas_sdk.models.reports import ReportSummaryRead

        def u(n: int) -> uuid.UUID:
            return uuid.UUID(f"00000000-0000-0000-0000-00000000000{n}")

        bv = BenchmarkVersionRead(
            id=u(2), benchmark_id=u(1), version_string="1.0.0",
            state="published",
        )
        self.list_benchmarks = lambda limit=50: PageResponse(
            items=[
                BenchmarkRead(id=u(1), project_id=u(9), name="B1", state="published")
            ],
            total=1, limit=limit, offset=0,
        )
        self.list_benchmark_versions = lambda benchmark_id: [bv]
        self.list_models = lambda: [
            ModelRead(
                id="mock", provider="test", display_name="Mock",
                status=ModelStatus.AVAILABLE,
            )
        ]
        self.submit_execution = (
            lambda bv_id, target_model="mock", dataset_version_id=None: ExecutionResponse(
                id=u(4), benchmark_version_id=uuid.UUID(str(bv_id)), status="QUEUED",
                target_model=target_model,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                updated_at=datetime(2026, 1, 1, tzinfo=UTC),
                created_by=u(9),
            )
        )
        self.get_execution = lambda execution_id: ExecutionResponse(
            id=uuid.UUID(str(execution_id)),
            benchmark_version_id=u(2),
            status="COMPLETED",
            target_model="mock",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            created_by=u(9),
        )
        self.get_report_run = lambda run_id: ReportSummaryRead(
            run_id=uuid.UUID(str(run_id)), benchmark_id=u(1), benchmark_name="B1",
            benchmark_version="1.0.0", target_model="mock",
            evaluation_status="COMPLETED", overall_score=92.5,
        )


def _make_loop(
    provider: FakeProvider,
    client: Any | None = None,
    *,
    now: Callable[[], datetime] | None = None,
    context: AgentContext | None = None,
) -> AgentLoop:
    return AgentLoop(
        provider=provider,  # type: ignore[arg-type]
        registry=ToolRegistry(),
        client=client or MockAtlasClient(),  # type: ignore[arg-type]
        now=now or (lambda: datetime(2026, 1, 1, tzinfo=UTC)),
        context=context,
    )


class TestFinalTextDirect:
    def test_final_text_returns_with_zero_tool_calls(self) -> None:
        provider = FakeProvider([_final("Here is the answer.")])
        loop = _make_loop(provider)
        result = loop.run("answer a question")
        assert isinstance(result, AgentResult)
        assert result.ok is True
        assert result.response == "Here is the answer."
        assert len(loop.context.tool_calls) == 0
        assert len(loop.context.observations) == 0


class TestMultiStepChain:
    def test_full_chain(self) -> None:
        provider = FakeProvider(
            [
                _tool("list_benchmarks"),
                _tool("get_benchmark_versions", benchmark_id=_id(1)),
                _tool("submit_run", benchmark_version_id=_id(2), target_model="mock"),
                _tool("watch_run", execution_id=_id(4), max_polls=1),
                _tool("get_report", run_id=_id(4)),
                _final("Run complete: score 92.5"),
            ]
        )
        loop = _make_loop(provider)
        result = loop.run("run and summarize the benchmark")
        assert result.ok is True
        assert result.response == "Run complete: score 92.5"
        names = [c.tool_name for c in loop.context.tool_calls]
        assert names == [
            "list_benchmarks",
            "get_benchmark_versions",
            "submit_run",
            "watch_run",
            "get_report",
        ]
        # every tool call has exactly one observation, with matching call_id
        assert len(loop.context.observations) == len(loop.context.tool_calls) == 5
        for call, obs in zip(loop.context.tool_calls, loop.context.observations, strict=True):
            assert obs.call_id == call.call_id
            assert obs.tool_name == call.tool_name
            assert obs.success is True
        assert loop.context.step_count == 6
        assert loop.context.completed_at is not None

    def test_context_transcript_accumulates(self) -> None:
        provider = FakeProvider(
            [_tool("list_benchmarks"), _final("done")]
        )
        loop = _make_loop(provider)
        loop.run("list benchmarks")
        first = provider.contexts[0]
        second = provider.contexts[1]
        assert "list_benchmarks" in second
        assert first != second


class TestUnknownTool:
    def test_unknown_tool_fails_cleanly_and_continues(self) -> None:
        provider = FakeProvider([_tool("nonexistent_tool", x=1), _final("recovered")])
        loop = _make_loop(provider)
        result = loop.run("do it")
        assert result.ok is True
        assert result.response == "recovered"
        assert loop.context.tool_calls[0].tool_name == "nonexistent_tool"
        obs = loop.context.observations[0]
        assert obs.success is False
        assert "unknown tool" in (obs.error or "").lower()


class TestToolFailure:
    def test_execute_exception_becomes_observation(self) -> None:
        class BoomClient(MockAtlasClient):
            def __init__(self) -> None:
                super().__init__()
                self.list_benchmarks = self._boom

            def _boom(self, limit=50):  # noqa: D401
                raise RuntimeError("backend exploded")

        provider = FakeProvider([_tool("list_benchmarks"), _final("recovered")])
        loop = _make_loop(provider, client=BoomClient())
        result = loop.run("list")
        assert result.ok is True
        assert result.response == "recovered"
        obs = loop.context.observations[0]
        assert obs.success is False
        assert "backend exploded" in (obs.error or "")

    def test_malformed_arguments_do_not_crash_cli(self) -> None:
        # get_benchmark_versions requires benchmark_id; missing -> validation error
        provider = FakeProvider([_tool("get_benchmark_versions"), _final("ok")])
        loop = _make_loop(provider)
        result = loop.run("version")
        assert result.ok is True
        obs = loop.context.observations[0]
        assert obs.success is False
        assert obs.error  # validation failure captured, not a thrown traceback


class TestFailDecision:
    def test_fail_decision_returns_error_result(self) -> None:
        provider = FakeProvider([_fail("model blew up")])
        loop = _make_loop(provider)
        result = loop.run("task")
        assert result.ok is False
        assert result.error == "model blew up"


class TestClarification:
    def test_clarification_returns_needs_more(self) -> None:
        provider = FakeProvider([_clarify("Which benchmark?"), _final("x")])
        loop = _make_loop(provider)
        result = loop.run("task")
        assert result.needs_clarification is True
        assert result.response == "Which benchmark?"


class TestStepLimit:
    def test_step_limit_raises_goal_exceeded(self) -> None:
        provider = FakeProvider([])  # fallback returns FINAL; make it loop forever
        provider._decisions = [_tool("list_benchmarks")] * (MAX_AGENT_STEPS + 1)
        loop = _make_loop(provider)
        with pytest.raises(GoalExceededError):
            loop.run("loop forever")
        # exactly MAX_AGENT_STEPS tool calls were performed before the loop hit
        # the step ceiling on the next iteration (bump_step increments first).
        assert len(loop.context.tool_calls) == MAX_AGENT_STEPS
        assert loop.context.total_tool_calls == MAX_AGENT_STEPS


class TestToolCallLimit:
    def test_tool_call_limit_raises_when_seeded_near_boundary(self) -> None:
        ctx = AgentContext(
            goal="seed",
            tool_calls=[], observations=[],
        )
        # seed the counter AT the tool-call ceiling without spending steps
        for _ in range(MAX_AGENT_TOOL_CALLS):
            ctx.record_tool_call(tool_name="list_benchmarks", arguments={})
        assert MAX_AGENT_TOOL_CALLS > MAX_AGENT_STEPS  # so step limit can't preempt
        provider = FakeProvider([_tool("list_benchmarks"), _final("x")])
        loop = _make_loop(provider, context=ctx)
        # ctx.step_count is 0, but the NEXT recorded call exceeds the ceiling
        with pytest.raises(GoalExceededError):
            loop.run("boundary")


class TestDeadline:
    def test_deadline_is_enforced_with_injected_clock(self) -> None:
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

        def ticking_now() -> datetime:
            return start + timedelta(seconds=AGENT_DEADLINE_SECONDS + 1)

        ctx = AgentContext(goal="slow", started_at=start)
        provider = FakeProvider([_tool("list_benchmarks"), _final("x")])
        loop = _make_loop(provider, now=ticking_now, context=ctx)
        with pytest.raises(GoalExceededError):
            loop.run("slow task")

    def test_before_deadline_runs_normally(self) -> None:
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

        def fresh_now() -> datetime:
            return start + timedelta(seconds=AGENT_DEADLINE_SECONDS - 1)

        provider = FakeProvider([_final("fast")])
        loop = _make_loop(provider, now=fresh_now, context=AgentContext(goal="g", started_at=start))
        result = loop.run("g")
        assert result.ok is True


class TestBuildContext:
    def test_build_context_renders_goal_and_transcript(self) -> None:
        provider = FakeProvider([_tool("list_benchmarks"), _final("done")])
        loop = _make_loop(provider)
        loop.run("list benchmarks")
        rendered = build_context(loop.context)
        assert "list benchmarks" in rendered
        assert "list_benchmarks" in rendered


class TestLoopConstruction:
    def test_context_is_created_from_goal(self) -> None:
        provider = FakeProvider([_final("hi")])
        loop = _make_loop(provider)
        loop.run("my goal")
        assert loop.context.goal == "my goal"
        assert loop.context.completed_at is not None
