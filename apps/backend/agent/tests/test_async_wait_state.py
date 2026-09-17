"""Regression tests: asynchronous execution waiting is a first-class agent state.

Production evidence (2026-08-23, agent_task_records d3c1e49e-56eb-44f5-a2d9-
753d957fe7d6): after PR #52 the progress fingerprint resets whenever the
OBSERVED execution state changes, but a GitHub Actions run legitimately sits
QUEUED with zero observable deltas while its runner provisions (the real
runner started ~12s after the agent was killed). The agent burned all 4
non-progress cycles in ~1.9 seconds of identical QUEUED polls.

Fix under test here:
- wait_for_runs tool: blocking, bounded-backoff, wall-clock-deadlined waiting.
- Plan-Progress Invariant exempts sanctioned waiting polls inside the
  deadline while tracked executions are non-terminal.
- Wait deadline expiry / WAIT_TIMEOUT produce explicit execution failures,
  and every non-waiting stuck loop still trips the invariant.
"""

from datetime import UTC, datetime
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import apps.backend.agent.tools.execution_tools as execution_tools
from atlas_db.core.base import Base
from atlas_db.core.session import SessionLocal
from atlas_db.models.execution import Execution as DBExecution
from atlas_db.models.execution import ExecutionStatus
from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.state import (
    AgentDecision,
    AgentDecisionType,
    AgentTask,
    AgentTaskStatus,
)
from apps.backend.agent.tools.execution_tools import WaitForRunsTool
from apps.backend.agent.tools.registry import ToolRegistry

EXEC_A = "aaaaaaaa-0000-0000-0000-00000000000a"
EXEC_B = "bbbbbbbb-0000-0000-0000-00000000000b"

TERMINAL_OK = ("COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT")


@pytest.fixture(autouse=True)
def _inline_execution_wait(monkeypatch):
    """These tests unit-test the inline waiter mechanics, which are now an
    explicit opt-out (AGENT_INLINE_EXECUTION_WAIT=true); production parks."""
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_inline_execution_wait", True, raising=False)


# ---------------------------------------------------------------------------
# Scripted-provider harness (mirrors test_async_polling_invariant.py)
# ---------------------------------------------------------------------------


class ProductionTraceProvider(BaseLLMProvider):
    """Replays the d3c1e49e shape: dispatch once, then fixate on ONE execution
    with byte-identical QUEUED polls until it turns terminal."""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.dispatched = False
        self.polls = 0

    def decide(self, task, context, declarations) -> AgentDecision:
        if self.dispatched:
            for obs in reversed(task.observations):
                if (
                    obs.tool_name == "get_run_status"
                    and isinstance(obs.output, dict)
                    and obs.output.get("execution_id") == self.execution_id
                    and str(obs.output.get("status")) in TERMINAL_OK
                ):
                    return AgentDecision(
                        type=AgentDecisionType.TOOL_CALL,
                        tool_name="generate_report",
                        arguments={"benchmark_id": "33333333-3333-3333-3333-333333333333"},
                        reasoning="Runs finished; publish report.",
                    )
            self.polls += 1
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="get_run_status",
                arguments={"execution_id": self.execution_id},
                reasoning=f"Poll #{self.polls} (identical args, like production).",
            )
        self.dispatched = True
        return AgentDecision(
            type=AgentDecisionType.TOOL_CALL,
            tool_name="run_benchmark",
            arguments={
                "benchmark_version_id": "11111111-1111-1111-1111-111111111111",
                "dataset_version_id": "22222222-2222-2222-2222-222222222222",
                "target_models": ["gemini-3.5-flash-lite"],
            },
            reasoning="Dispatch remote run.",
        )


class DispatchThenWaitProvider(BaseLLMProvider):
    """Dispatches, calls wait_for_runs once, then finishes."""

    def __init__(self):
        self.stage = 0

    def decide(self, task, context, declarations) -> AgentDecision:
        self.stage += 1
        if self.stage == 1:
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="run_benchmark",
                arguments={
                    "benchmark_version_id": "11111111-1111-1111-1111-111111111111",
                    "dataset_version_id": "22222222-2222-2222-2222-222222222222",
                    "target_models": ["mock"],
                },
                reasoning="Dispatch.",
            )
        if self.stage == 2:
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="wait_for_runs",
                arguments={"execution_ids": list(task.execution_ids)},
                reasoning="Block until terminal.",
            )
        return AgentDecision(
            type=AgentDecisionType.TOOL_CALL,
            tool_name="generate_report",
            arguments={"benchmark_id": "33333333-3333-3333-3333-333333333333"},
            reasoning="Runs finished; publish report.",
        )


class _NoopPlanner:
    def generate_initial_plan(self, goal, run_mode=None):
        return []

    def update_plan_on_decision(self, task, decision, output):
        return None


def _allow_all_tools(monkeypatch) -> None:
    """Unit-test harness: bypass the interactive approval gate."""
    monkeypatch.setattr(ToolRegistry, "check_permission", lambda self, tool_name, perms: True)


def _stub_registry(monkeypatch, status_sequences: dict[str, list[dict]]):
    counters = {eid: 0 for eid in status_sequences}

    def fake_execute(self, tool_name=None, db=None, arguments=None, **kwargs):
        if tool_name == "run_benchmark":
            eids = [EXEC_A, EXEC_B][: 1 + (len(arguments.get("target_models", [])) > 1)]
            return {
                "status": "DISPATCHED",
                "execution_ids": [str(e) for e in eids],
            }
        if tool_name == "generate_report":
            return {
                "status": "PUBLISHED",
                "published": True,
                "report_id": str(uuid.uuid4()),
                "summary": "Benchmark evaluation completed successfully.",
            }
        if tool_name == "get_run_status":
            eid = arguments["execution_id"]
            seq = status_sequences[eid]
            idx = min(counters[eid], len(seq) - 1)
            counters[eid] += 1
            out = dict(seq[idx])
            out.setdefault("execution_id", eid)
            return out
        raise AssertionError(f"unexpected tool {tool_name}")

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


# ---------------------------------------------------------------------------
# Agent-loop level: the production trace must now succeed
# ---------------------------------------------------------------------------


def test_production_trace_replay_static_queued_polls_survive(monkeypatch):
    """EXACT d3c1e49e shape: dispatch -> >=4 byte-identical QUEUED polls within
    ~2s -> COMPLETED. The old invariant killed this at the 4th poll; the
    sanctioned wait phase must carry the task through."""
    _allow_all_tools(monkeypatch)
    _stub_registry(monkeypatch, {EXEC_A: _statuses(["QUEUED"]) * 6 + _statuses(["COMPLETED"])})
    task = AgentTask(goal="make a benchmark for counting upto 77", primary_provider="test")
    task._scripted_provider = ProductionTraceProvider(EXEC_A)  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.COMPLETED, done.error_detail
    assert "PROGRESS_INVARIANT_VIOLATION" not in [t.event_type for t in done.execution_trace]
    assert done.execution_wait_started_at is not None
    queued_identical_polls = sum(
        1
        for o in done.observations
        if o.tool_name == "get_run_status"
        and isinstance(o.output, dict)
        and o.output.get("status") == "QUEUED"
    )
    assert queued_identical_polls >= 4, "fixture must reproduce the fatal stall"


def test_wait_deadline_expiry_reactivates_invariant(monkeypatch):
    """Once the wall-clock deadline is exhausted, static non-terminal polling
    is no longer sanctioned and the invariant must fire again."""
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_execution_wait_deadline_seconds", 0)
    _stub_registry(monkeypatch, {EXEC_A: _statuses(["QUEUED"])})
    task = AgentTask(goal="stuck after deadline", primary_provider="test")
    task._scripted_provider = ProductionTraceProvider(EXEC_A)  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.FAILED
    assert "Plan-Progress Invariant Violation" in (done.error_detail or "")


def test_wait_timeout_converts_to_explicit_execution_failure(monkeypatch):
    """wait_for_runs reporting WAIT_TIMEOUT fails the task with a clear
    execution-timeout error, not a Plan-Progress Invariant Violation."""

    class TimeoutWaitRegistry:
        @staticmethod
        def install(monkeypatch):
            def fake_execute(self, tool_name=None, db=None, arguments=None, **kwargs):
                if tool_name == "run_benchmark":
                    return {
                        "status": "DISPATCHED",
                        "execution_ids": [EXEC_A],
                    }
                if tool_name == "wait_for_runs":
                    return {
                        "status": "WAIT_TIMEOUT",
                        "waited_seconds": 480.0,
                        "executions": {EXEC_A: {"execution_id": EXEC_A, "status": "QUEUED"}},
                        "non_terminal_execution_ids": [EXEC_A],
                        "message": f"Wait deadline of 480s exceeded; executions still in flight: {EXEC_A}=QUEUED",
                    }
                raise AssertionError(f"unexpected tool {tool_name}")

            monkeypatch.setattr(ToolRegistry, "execute", fake_execute)

    TimeoutWaitRegistry.install(monkeypatch)
    task = AgentTask(goal="prolonged running run", primary_provider="test")
    task._scripted_provider = DispatchThenWaitProvider()  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.FAILED
    assert "Execution wait timeout" in (done.error_detail or "")
    assert "Plan-Progress Invariant" not in (done.error_detail or "")
    assert any(t.event_type == "EXECUTION_WAIT_TIMEOUT" for t in done.execution_trace)


def test_wait_for_runs_tool_success_path_completes_loop(monkeypatch):
    """Dispatch -> blocking wait returning COMPLETED -> task completes."""
    _allow_all_tools(monkeypatch)
    wait_results = iter(
        [
            {
                "status": "COMPLETED",
                "waited_seconds": 61.3,
                "executions": {EXEC_A: {"execution_id": EXEC_A, "status": "COMPLETED"}},
                "message": "All executions reached a terminal state.",
            }
        ]
    )

    def fake_execute(self, tool_name=None, db=None, arguments=None, **kwargs):
        if tool_name == "run_benchmark":
            return {"status": "DISPATCHED", "execution_ids": [EXEC_A]}
        if tool_name == "wait_for_runs":
            return next(wait_results)
        if tool_name == "generate_report":
            return {
                "status": "PUBLISHED",
                "published": True,
                "report_id": str(uuid.uuid4()),
                "summary": "Benchmark evaluation completed successfully.",
            }
        raise AssertionError(f"unexpected tool {tool_name}")

    monkeypatch.setattr(ToolRegistry, "execute", fake_execute)
    task = AgentTask(goal="happy path", primary_provider="test")
    task._scripted_provider = DispatchThenWaitProvider()  # type: ignore[attr-defined]
    done = _run(task)

    assert done.status == AgentTaskStatus.COMPLETED, done.error_detail


# ---------------------------------------------------------------------------
# Tool-level: WaitForRunsTool against a real (sqlite) session
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_execution(db, eid: str, status: ExecutionStatus) -> None:
    db.add(
        DBExecution(
            id=uuid.UUID(eid),
            project_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            dataset_version_id=uuid.uuid4(),
            target_model="mock",
            status=status,
        )
    )
    db.commit()


def test_wait_lifecycle_queued_running_completed(db_session, monkeypatch):
    """QUEUED -> RUNNING -> COMPLETED across backoff ticks succeeds, using the
    exponential schedule."""
    _seed_execution(db_session, EXEC_A, ExecutionStatus.QUEUED)
    sleeps: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleeps.append(delay)
        row = db_session.query(DBExecution).filter(DBExecution.id == uuid.UUID(EXEC_A)).first()
        row.status = ExecutionStatus.RUNNING if len(sleeps) == 1 else ExecutionStatus.COMPLETED
        db_session.commit()

    monkeypatch.setattr(execution_tools, "_sleep", fake_sleep)
    res = WaitForRunsTool().execute(db=db_session, execution_ids=[EXEC_A])

    assert res["status"] == "COMPLETED"
    assert sleeps[:2] == list(execution_tools.WAIT_POLL_SCHEDULE_S)[:2]
    assert res["executions"][EXEC_A]["status"] == "COMPLETED"


def test_wait_timeout_returns_pending_ids(db_session, monkeypatch):
    """Prolonged non-terminal state hits the caller-supplied deadline and
    reports WAIT_TIMEOUT with the still-pending execution ids."""
    _seed_execution(db_session, EXEC_A, ExecutionStatus.QUEUED)
    monkeypatch.setattr(
        execution_tools,
        "_sleep",
        lambda _d: (_ for _ in ()).throw(AssertionError("must not sleep")),
    )

    res = WaitForRunsTool().execute(db=db_session, execution_ids=[EXEC_A], timeout_seconds=0)

    assert res["status"] == "WAIT_TIMEOUT"
    assert res["non_terminal_execution_ids"] == [EXEC_A]
    assert "deadline" in res["message"]


@pytest.mark.parametrize(
    "status", [ExecutionStatus.FAILED, ExecutionStatus.CANCELLED, ExecutionStatus.TIMED_OUT]
)
def test_terminal_failure_states_stop_immediately(db_session, monkeypatch, status):
    """FAILED / CANCELLED / TIMED_OUT terminate the wait instantly with an
    explicit EXECUTION_FAILED summary and zero sleeping."""
    _seed_execution(db_session, EXEC_A, status)
    monkeypatch.setattr(
        execution_tools,
        "_sleep",
        lambda _d: (_ for _ in ()).throw(AssertionError("no sleep expected")),
    )

    res = WaitForRunsTool().execute(db=db_session, execution_ids=[EXEC_A])

    assert res["status"] == "EXECUTION_FAILED"
    assert res["executions"][EXEC_A]["status"] == status.value


def test_multiple_executions_tracked_independently(db_session, monkeypatch):
    """Two concurrent runs: A already terminal, B flips after one tick. The
    wait resolves only when BOTH are terminal, reporting each independently."""
    _seed_execution(db_session, EXEC_A, ExecutionStatus.COMPLETED)
    _seed_execution(db_session, EXEC_B, ExecutionStatus.QUEUED)
    sleeps: list[float] = []

    def fake_sleep(_delay: float) -> None:
        sleeps.append(_delay)
        row = db_session.query(DBExecution).filter(DBExecution.id == uuid.UUID(EXEC_B)).first()
        row.status = ExecutionStatus.COMPLETED
        db_session.commit()

    monkeypatch.setattr(execution_tools, "_sleep", fake_sleep)
    res = WaitForRunsTool().execute(db=db_session, execution_ids=[EXEC_A, EXEC_B])

    assert res["status"] == "COMPLETED"
    assert res["executions"][EXEC_A]["status"] == "COMPLETED"
    assert res["executions"][EXEC_B]["status"] == "COMPLETED"
    assert len(sleeps) == 1


def test_synchronous_already_terminal_no_sleep(db_session, monkeypatch):
    """Local/eager backends finish instantly: pre-terminal executions return
    immediately without a single sleep (sync behaviour unchanged)."""
    _seed_execution(db_session, EXEC_A, ExecutionStatus.COMPLETED)
    monkeypatch.setattr(
        execution_tools,
        "_sleep",
        lambda _d: (_ for _ in ()).throw(AssertionError("no sleep expected")),
    )

    res = WaitForRunsTool().execute(db=db_session, execution_ids=[EXEC_A])

    assert res["status"] == "COMPLETED"
    assert res["executions"][EXEC_A]["status"] == "COMPLETED"


def test_wait_requires_execution_ids(db_session):
    with pytest.raises(ValueError, match="execution_ids"):
        WaitForRunsTool().execute(db=db_session)
