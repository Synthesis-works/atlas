"""Regression tests for async execution polling vs. the Plan-Progress Invariant.

Production evidence (2026-08-23, Supabase agent_task_records): with the GitHub
Actions execution backend, run_benchmark dispatches asynchronously and the
agent must poll get_run_status several times. The old fingerprint treated
repeated identical polls as zero progress and killed healthy tasks after 4
cycles while the remote run was still in flight.

These tests script an LLM provider that polls get_run_status and stub the tool
registry with deterministic status sequences - no network, no real providers.
"""

import pytest

from atlas_db.core.session import SessionLocal
from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.state import (
    AgentDecision,
    AgentDecisionType,
    AgentTask,
    AgentTaskStatus,
)

EXEC_A = "aaaaaaaa-0000-0000-0000-00000000000a"
EXEC_B = "bbbbbbbb-0000-0000-0000-00000000000b"

TERMINAL_OK = ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT")


class PollingProvider(BaseLLMProvider):
    """Polls get_run_status until the observation reports a terminal state."""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.polls = 0

    def decide(self, task, context, declarations) -> AgentDecision:
        last = self._last_observation(task)
        if last is not None and str(last.get("status", "")) in TERMINAL_OK:
            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response=f"Execution finished with {last.get('status')}.",
                reasoning="Terminal state observed.",
            )
        self.polls += 1
        return AgentDecision(
            type=AgentDecisionType.TOOL_CALL,
            tool_name="get_run_status",
            arguments={"execution_id": self.execution_id},
            reasoning=f"Poll #{self.polls} for async execution.",
        )

    @staticmethod
    def _last_observation(task) -> dict | None:
        for obs in reversed(task.observations):
            if obs.tool_name == "get_run_status" and isinstance(obs.output, dict):
                return obs.output
        return None


class TwoExecutionPollingProvider(BaseLLMProvider):
    """Polls stalled execution A twice per cycle, progressing execution B
    slowly (Q -> R -> C). Stops once B is terminal."""

    def __init__(self, exec_a: str, exec_b: str):
        self.exec_a = exec_a
        self.exec_b = exec_b
        self.b_polls = 0

    def decide(self, task, context, declarations) -> AgentDecision:
        b_state = None
        for obs in reversed(task.observations):
            if (
                obs.tool_name == "get_run_status"
                and isinstance(obs.output, dict)
                and obs.output.get("execution_id") == self.exec_b
            ):
                b_state = str(obs.output.get("status", ""))
                break
        if b_state in TERMINAL_OK:
            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response=f"B reached {b_state}.",
                reasoning="Progressed execution finished.",
            )
        # Two A-polls back-to-back would kill an unreset counter within two
        # B-cycles; surviving this pattern proves B's changes reset progress.
        a_polls = sum(
            1
            for o in task.observations
            if o.tool_name == "get_run_status"
            and isinstance(o.output, dict)
            and o.output.get("execution_id") == self.exec_a
        )
        if a_polls <= 2 * self.b_polls:
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="get_run_status",
                arguments={"execution_id": self.exec_a},
                reasoning="Poll stalled execution.",
            )
        self.b_polls += 1
        return AgentDecision(
            type=AgentDecisionType.TOOL_CALL,
            tool_name="get_run_status",
            arguments={"execution_id": self.exec_b},
            reasoning="Poll progressing execution.",
        )


def _stub_registry(monkeypatch, sequences: dict[str, list[dict]]):
    """Replace registry.execute so get_run_status pops scripted status dicts."""
    counters = {eid: 0 for eid in sequences}

    def fake_execute(self, tool_name=None, db=None, arguments=None, **kwargs):
        if tool_name == "get_run_status":
            eid = arguments["execution_id"]
            seq = sequences[eid]
            idx = min(counters[eid], len(seq) - 1)
            counters[eid] += 1
            out = dict(seq[idx])
            out.setdefault("execution_id", eid)
            return out
        raise AssertionError(f"unexpected tool {tool_name}")

    from apps.backend.agent.tools.registry import ToolRegistry

    monkeypatch.setattr(ToolRegistry, "execute", fake_execute)


def _statuses(statuses: list[str]) -> list[dict]:
    return [
        {"status": s, "progress": "50%", "completed_items": 1, "total_items": 2} for s in statuses
    ]


def _run(task: AgentTask) -> AgentTask:
    agent = AtlasAgent(
        provider=task._scripted_provider,  # type: ignore[attr-defined]
        planner=_NoopPlanner(),
    )
    with SessionLocal() as db:
        return agent.run_task(task, db)


class _NoopPlanner:
    """Empty plan keeps these tests focused on the invariant mechanics
    (production traces showed all plan steps already COMPLETED while the
    polling stall happened)."""

    def generate_initial_plan(self, goal, run_mode=None):
        return []

    def update_plan_on_decision(self, task, decision, output):
        return None


def test_repro_production_failure_completed_run_killed_by_invariant(monkeypatch):
    """Original production failure: GHA finishes QUEUED->RUNNING->COMPLETED but
    the agent was killed by the invariant mid-poll. Must now succeed."""
    _stub_registry(monkeypatch, {EXEC_A: _statuses(["QUEUED", "RUNNING", "COMPLETED"])})
    task = AgentTask(goal="create a benchmark", primary_provider="test")
    task._scripted_provider = PollingProvider(EXEC_A)  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.COMPLETED, done.error_detail
    assert done.consecutive_non_progress_steps < 4


def test_stuck_queued_polling_still_triggers_invariant(monkeypatch):
    _stub_registry(monkeypatch, {EXEC_A: _statuses(["QUEUED"])})
    task = AgentTask(goal="create a benchmark", primary_provider="test")
    task._scripted_provider = PollingProvider(EXEC_A)  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.FAILED
    assert "Plan-Progress Invariant Violation" in (done.error_detail or "")


def test_stuck_running_polling_still_triggers_invariant(monkeypatch):
    _stub_registry(monkeypatch, {EXEC_A: _statuses(["RUNNING"])})
    task = AgentTask(goal="create a benchmark", primary_provider="test")
    task._scripted_provider = PollingProvider(EXEC_A)  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.FAILED
    assert "Plan-Progress Invariant Violation" in (done.error_detail or "")


def test_status_change_resets_non_progress_counter(monkeypatch):
    """More than 4 identical QUEUED polls in total, but each RUNNING blip resets
    the counter - the task must survive and finish."""
    seq = ["QUEUED", "QUEUED", "QUEUED", "RUNNING"] * 3 + ["COMPLETED"]
    _stub_registry(monkeypatch, {EXEC_A: _statuses(seq)})
    task = AgentTask(goal="create a benchmark", primary_provider="test")
    task._scripted_provider = PollingProvider(EXEC_A)  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.COMPLETED, done.error_detail


def test_executions_are_fingerprinted_independently(monkeypatch):
    """A stalls in QUEUED forever while B progresses Q->R->C. B's transitions
    must count as progress (per-execution keying), letting the loop continue
    despite long runs of identical A-polls."""
    _stub_registry(
        monkeypatch,
        {
            EXEC_A: _statuses(["QUEUED"]),
            EXEC_B: _statuses(["QUEUED", "RUNNING", "COMPLETED"]),
        },
    )
    task = AgentTask(goal="create a benchmark", primary_provider="test")
    provider = TwoExecutionPollingProvider(EXEC_A, EXEC_B)
    task._scripted_provider = provider  # type: ignore[attr-defined]

    # Direct fingerprint check: differing B-state => different fingerprint,
    # with A's observed state identical in both tasks.
    agent = AtlasAgent(provider=MockLike())
    t1 = AgentTask(goal="g", primary_provider="test")
    t2 = AgentTask(goal="g", primary_provider="test")
    for t, bstat in ((t1, "QUEUED"), (t2, "COMPLETED")):
        t.tool_calls.append(_call("get_run_status", {"execution_id": EXEC_A}))
        t.observations.append(_obs("get_run_status", EXEC_A, "RUNNING"))
        t.tool_calls.append(_call("get_run_status", {"execution_id": EXEC_B}))
        t.observations.append(_obs("get_run_status", EXEC_B, bstat))
    fp1 = agent._get_progress_fingerprint(t1)
    fp2 = agent._get_progress_fingerprint(t2)
    assert fp1[-1] != fp2[-1], "B-status change must alter the fingerprint"
    assert fp1 != fp2

    done = _run(task)
    assert done.status == AgentTaskStatus.COMPLETED, done.error_detail
    a_polls = sum(
        1
        for o in done.observations
        if o.tool_name == "get_run_status"
        and isinstance(o.output, dict)
        and o.output.get("execution_id") == EXEC_A
    )
    assert a_polls >= 4, "must survive at least 4 static A-polls thanks to B resets"


def test_failed_terminal_state_exits_polling_cleanly(monkeypatch):
    _stub_registry(monkeypatch, {EXEC_A: _statuses(["RUNNING", "FAILED"])})
    task = AgentTask(goal="create a benchmark", primary_provider="test")
    task._scripted_provider = PollingProvider(EXEC_A)  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.COMPLETED
    assert any(
        "FAILED" in str(o.output)
        for o in done.observations
        if o.tool_name == "get_run_status" and isinstance(o.output, dict)
    )


def test_endless_failed_polling_preserves_invariant(monkeypatch):
    """Terminal-but-static polling is still a stuck loop."""
    _stub_registry(monkeypatch, {EXEC_A: _statuses(["FAILED"])})
    task = AgentTask(goal="create a benchmark", primary_provider="test")
    task._scripted_provider = _StaticPoller(EXEC_A)  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.FAILED
    assert "Plan-Progress Invariant Violation" in (done.error_detail or "")


class _StaticPoller(BaseLLMProvider):
    """Unconditionally polls the same execution - models a confused agent."""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id

    def decide(self, task, context, declarations) -> AgentDecision:
        return AgentDecision(
            type=AgentDecisionType.TOOL_CALL,
            tool_name="get_run_status",
            arguments={"execution_id": self.execution_id},
            reasoning="Static polling.",
        )


def test_synchronous_stuck_loop_unchanged(monkeypatch):
    """Pre-existing behaviour: repeating a NON-polling tool stays a violation."""
    from apps.backend.agent.tools.registry import ToolRegistry

    class StuckProvider(BaseLLMProvider):
        def decide(self, task, context, declarations) -> AgentDecision:
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="get_available_models",
                arguments={},
                reasoning="stuck",
            )

    monkeypatch.setattr(ToolRegistry, "execute", lambda self, **kw: {"available_models": []})
    task = AgentTask(goal="simulate stuck sync agent", primary_provider="test")
    agent = AtlasAgent(provider=StuckProvider())
    with SessionLocal() as db:
        done = agent.run_task(task, db)

    assert done.status == AgentTaskStatus.FAILED
    assert "Plan-Progress Invariant Violation" in (done.error_detail or "")
    assert done.consecutive_non_progress_steps == 4


def _call(tool_name, args):
    from apps.backend.agent.state import ToolCallRecord

    return ToolCallRecord(call_id=f"c_{tool_name}_{args}", tool_name=tool_name, arguments=args)


def _obs(tool_name, eid, status):
    from apps.backend.agent.state import ObservationRecord

    return ObservationRecord(
        call_id=f"o_{eid}_{status}",
        tool_name=tool_name,
        success=True,
        output={"execution_id": eid, "status": status},
    )


class MockLike(BaseLLMProvider):
    def decide(self, task, context, declarations) -> AgentDecision:
        raise AssertionError("not used in fingerprint unit checks")
