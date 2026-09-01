"""Tests for the CLI agent shared state & limits (Phase 1).

Mirrors the backend agent's ``AgentDecision``/limit shape but scoped to the
client-side CLI agent.
"""

from __future__ import annotations

import pytest

from cli.agent.state import (
    AGENT_DEADLINE_SECONDS,
    MAX_AGENT_STEPS,
    MAX_AGENT_TOOL_CALLS,
    AgentContext,
    AgentDecision,
    AgentDecisionType,
    AgentLimitError,
    GoalExceededError,
    ToolCallRecord,
)


class TestLimits:
    def test_limits_are_sane(self) -> None:
        assert MAX_AGENT_STEPS > 0
        assert MAX_AGENT_TOOL_CALLS >= MAX_AGENT_STEPS
        assert AGENT_DEADLINE_SECONDS > 0

    def test_goal_exceeded_error_is_agent_limit_error(self) -> None:
        assert issubclass(GoalExceededError, AgentLimitError)


class TestAgentDecision:
    def test_default_tool_call_decision(self) -> None:
        d = AgentDecision(
            type=AgentDecisionType.TOOL_CALL,
            tool_name="model_list",
            arguments={"format": "json"},
        )
        assert d.tool_name == "model_list"
        assert d.arguments == {"format": "json"}
        assert d.response is None
        assert d.error_message is None

    def test_final_response_decision(self) -> None:
        d = AgentDecision(type=AgentDecisionType.FINAL_RESPONSE, response="done")
        assert d.response == "done"
        assert d.tool_name is None

    def test_fail_decision_carries_error(self) -> None:
        d = AgentDecision(type=AgentDecisionType.FAIL, error_message="boom")
        assert d.error_message == "boom"

    def test_decision_serializes(self) -> None:
        d = AgentDecision(type=AgentDecisionType.TOOL_CALL, tool_name="run_submit")
        dumped = d.model_dump_json()
        assert '"type":"TOOL_CALL"' in dumped
        assert '"tool_name":"run_submit"' in dumped


class TestAgentContext:
    def test_goal_capture_and_records(self) -> None:
        ctx = AgentContext(goal="list benchmarks and runs")
        assert ctx.goal == "list benchmarks and runs"
        assert ctx.tool_calls == []
        assert ctx.observations == []
        assert ctx.step_count == 0
        assert ctx.total_tool_calls == 0

    def test_record_tool_call_appends_and_counts(self) -> None:
        ctx = AgentContext(goal="g")
        rec = ctx.record_tool_call(tool_name="model_list", arguments={"x": 1})
        assert rec.tool_name == "model_list"
        assert ctx.total_tool_calls == 1
        assert len(ctx.tool_calls) == 1

    def test_record_observation_appends(self) -> None:
        ctx = AgentContext(goal="g")
        ctx.record_observation(
            call_id="c1", tool_name="benchmark_list", success=True, output=[],
        )
        assert len(ctx.observations) == 1
        assert ctx.observations[0].success is True

    def test_goal_exceeded_when_steps_over_limit(self) -> None:
        ctx = AgentContext(goal="g")
        with pytest.raises(GoalExceededError):
            ctx.bump_step(MAX_AGENT_STEPS + 1)

    def test_goal_exceeded_when_tool_calls_over_limit(self) -> None:
        ctx = AgentContext(goal="g")
        for _ in range(MAX_AGENT_TOOL_CALLS):
            ctx.record_tool_call(tool_name="model_list", arguments={})
        with pytest.raises(GoalExceededError):
            ctx.record_tool_call(tool_name="benchmark_list", arguments={})

    def test_bump_step_increments(self) -> None:
        ctx = AgentContext(goal="g")
        ctx.bump_step()
        ctx.bump_step()
        assert ctx.step_count == 2


class TestToolCallRecord:
    def test_defaults(self) -> None:
        rec = ToolCallRecord(tool_name="run_get", arguments={})
        assert rec.call_id
        assert rec.timestamp
        assert rec.tool_name == "run_get"
