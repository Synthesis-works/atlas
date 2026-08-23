"""Event-driven agent resume: lifecycle regression suite.

Reproduces the PR #54 production failure mode (serverless function killed
while waiting on GitHub Actions) and proves the WAITING_FOR_EXECUTION park +
outbox-event resume lifecycle end to end. See docs/AGENT_TASK_LIFECYCLE.md.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from atlas_db.models.agent import AgentTaskRecord
from atlas_db.models.execution import Execution as DBExecution
from atlas_db.models.execution import ExecutionStatus
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.state import (
    AgentDecision,
    AgentDecisionType,
    AgentTask,
    AgentTaskStatus,
)
from apps.backend.worker.agent_resume import (
    MAX_RESUME_ATTEMPTS,
    AgentTaskResumeSubscriber,
    claim_waiting_task,
    find_waiting_tasks_for_execution,
    handle_terminal_execution_event,
    recover_stale_waiting_tasks,
    resume_agent_task_core,
)

EXEC_A = "aaaaaaaa-0000-0000-0000-00000000000a"
EXEC_B = "bbbbbbbb-0000-0000-0000-00000000000b"
BENCHMARK_ID = "33333333-3333-3333-3333-333333333333"


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _snapshot(execution_ids, **overrides):
    task = AgentTask(
        goal="make a benchmark for counting upto 77",
        primary_provider="gemini",
        status=AgentTaskStatus.WAITING_FOR_EXECUTION,
        execution_ids=list(execution_ids),
        step_count=9,
        waiting_since=datetime.now(UTC),
    )
    data = task.model_dump(mode="json")
    for key, value in overrides.items():
        data[key] = value.isoformat() if isinstance(value, datetime) else value
    return data


def _seed_waiting(db, eids, status=AgentTaskStatus.WAITING_FOR_EXECUTION.value, **ovr):
    record = AgentTaskRecord(
        task_id=uuid.uuid4(),
        goal="make a benchmark for counting upto 77",
        status=status,
        snapshot=_snapshot(eids, **ovr),
    )
    db.add(record)
    db.commit()
    return record


def _seed_exec(db, eid, status):
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


class ReportOnResumeProvider(BaseLLMProvider):
    def decide(self, task, context, declarations) -> AgentDecision:
        return AgentDecision(
            type=AgentDecisionType.TOOL_CALL,
            tool_name="generate_report",
            arguments={"benchmark_id": BENCHMARK_ID},
            reasoning="All runs terminal after resume; publishing report.",
        )


@pytest.fixture
def report_registry(monkeypatch):
    from apps.backend.agent.tools.registry import ToolRegistry

    counter = {"generate_report": 0}

    def fake_execute(self, tool_name=None, db=None, arguments=None, **kwargs):
        if tool_name == "generate_report":
            counter["generate_report"] += 1
            return {
                "status": "PUBLISHED",
                "published": True,
                "report_id": str(uuid.uuid4()),
                "summary": "Benchmark evaluation completed successfully.",
            }
        raise AssertionError(f"unexpected tool {tool_name}")

    monkeypatch.setattr(ToolRegistry, "execute", fake_execute)
    monkeypatch.setattr(ToolRegistry, "check_permission", lambda self, t, p: True)
    return counter


# --- 1. PR #54 reproduction -------------------------------------------------


def test_pr54_reproduction_process_death_then_event_resume_completes(db, report_registry):
    """Vercel process died mid-wait; GHA completed later; event resumes task."""
    _seed_exec(db, EXEC_A, ExecutionStatus.COMPLETED)
    record = _seed_waiting(db, [EXEC_A])

    outcomes = handle_terminal_execution_event(
        db,
        uuid.UUID(EXEC_A),
        "ExecutionCompletedEvent",
        provider_factory=lambda _t: ReportOnResumeProvider(),
    )

    assert outcomes == ["COMPLETED"]
    db.refresh(record)
    assert record.status == AgentTaskStatus.COMPLETED.value
    snap = record.snapshot
    assert snap["error_detail"] is None
    assert snap["report_id"] is not None
    trace = [t["event_type"] for t in snap["execution_trace"]]
    assert "AGENT_TASK_RESUMED" in trace
    assert "TASK_COMPLETED" in trace
    assert report_registry["generate_report"] == 1


def test_default_provider_factory_builds_router():
    """Default factory wires ProviderRouter without invoking any provider."""
    from apps.backend.agent.providers.router import ProviderRouter
    from apps.backend.worker.agent_resume import _default_provider_factory

    task = AgentTask(goal="g", primary_provider="gemini")
    router = _default_provider_factory(task)
    assert isinstance(router, ProviderRouter)


def test_resume_synthesizes_missing_terminal_observation(db, report_registry):
    captured = {}

    def factory(task):
        captured["obs"] = list(task.observations)
        return ReportOnResumeProvider()

    _seed_exec(db, EXEC_A, ExecutionStatus.COMPLETED)
    record = _seed_waiting(db, [EXEC_A])

    resume_agent_task_core(
        db,
        record.task_id,
        event_type="ExecutionCompletedEvent",
        provider_factory=factory,
    )

    synth = [o for o in captured["obs"] if isinstance(o.output, dict) and o.output.get("resumed")]
    assert len(synth) == 1
    assert synth[0].output["status"] == "COMPLETED"


# --- 2-4. Idempotency --------------------------------------------------------


def test_duplicate_completion_event_is_noop(db, report_registry):
    _seed_exec(db, EXEC_A, ExecutionStatus.COMPLETED)
    record = _seed_waiting(db, [EXEC_A])
    factory = lambda _t: ReportOnResumeProvider()  # noqa: E731

    first = handle_terminal_execution_event(
        db,
        uuid.UUID(EXEC_A),
        "ExecutionCompletedEvent",
        provider_factory=factory,
    )
    assert first == ["COMPLETED"]

    outcomes = handle_terminal_execution_event(
        db,
        uuid.UUID(EXEC_A),
        "ExecutionCompletedEvent",
        provider_factory=factory,
    )

    assert outcomes == []
    assert report_registry["generate_report"] == 1
    db.refresh(record)
    assert record.status == AgentTaskStatus.COMPLETED.value


def test_claim_requires_waiting_status(db):
    record = _seed_waiting(db, [EXEC_A], status=AgentTaskStatus.COMPLETED.value)

    assert claim_waiting_task(db, record.task_id) is None


def test_completion_before_waiting_persist_recovered_by_sweep(db, report_registry):
    """Completion event swept before the WAITING row existed -> sweep resumes."""
    _seed_exec(db, EXEC_A, ExecutionStatus.COMPLETED)
    # Event arrives first: nothing to do yet.
    assert handle_terminal_execution_event(db, uuid.UUID(EXEC_A), "ExecutionCompletedEvent") == []

    # Late persist of the parked snapshot (race window).
    record = _seed_waiting(db, [EXEC_A])
    summary = recover_stale_waiting_tasks(db, provider_factory=lambda _t: ReportOnResumeProvider())

    assert summary["resumed"] == 1
    db.refresh(record)
    assert record.status == AgentTaskStatus.COMPLETED.value
    assert report_registry["generate_report"] == 1


# --- 5-6. Failure branches ----------------------------------------------------


def _never_called_factory(_task):
    raise AssertionError("provider must not run for failure outcomes")


def test_execution_failure_branch(db):
    """Partial failure: A COMPLETED + B FAILED -> task FAILED, no LLM call."""
    _seed_exec(db, EXEC_A, ExecutionStatus.COMPLETED)
    _seed_exec(db, EXEC_B, ExecutionStatus.FAILED)
    record = _seed_waiting(db, [EXEC_A, EXEC_B])

    outcomes = handle_terminal_execution_event(
        db,
        uuid.UUID(EXEC_B),
        "ExecutionFailedEvent",
        error_message="docker container exited 1",
        provider_factory=_never_called_factory,
    )

    assert outcomes == ["EXECUTION_FAILED"]
    db.refresh(record)
    snap = record.snapshot
    assert record.status == AgentTaskStatus.FAILED.value
    assert snap["error_detail"].startswith("EXECUTION_FAILED")
    trace = [t["event_type"] for t in snap["execution_trace"]]
    assert "EXECUTION_TERMINAL_FAILURE" in trace


def test_timed_out_branch_resolved_from_db_status(db):
    _seed_exec(db, EXEC_A, ExecutionStatus.TIMED_OUT)
    record = _seed_waiting(db, [EXEC_A])

    outcomes = handle_terminal_execution_event(
        db,
        uuid.UUID(EXEC_A),
        "ExecutionFailedEvent",
        error_message="Execution timed out",
        provider_factory=_never_called_factory,
    )

    assert outcomes == ["EXECUTION_TIMED_OUT"]
    db.refresh(record)
    assert record.snapshot["error_detail"].startswith("EXECUTION_TIMED_OUT")


def test_cancelled_branch(db):
    _seed_exec(db, EXEC_A, ExecutionStatus.CANCELLED)
    record = _seed_waiting(db, [EXEC_A])

    outcomes = handle_terminal_execution_event(
        db,
        uuid.UUID(EXEC_A),
        "ExecutionCancelledEvent",
        provider_factory=_never_called_factory,
    )

    assert outcomes == ["EXECUTION_CANCELLED"]
    db.refresh(record)
    assert record.snapshot["error_detail"].startswith("EXECUTION_CANCELLED")


def test_inflight_sibling_defers_resume(db, report_registry):
    """A completed but B still RUNNING: task stays WAITING for B's event."""
    _seed_exec(db, EXEC_A, ExecutionStatus.COMPLETED)
    _seed_exec(db, EXEC_B, ExecutionStatus.RUNNING)
    record = _seed_waiting(db, [EXEC_A, EXEC_B])

    outcomes = handle_terminal_execution_event(db, uuid.UUID(EXEC_A), "ExecutionCompletedEvent")

    assert outcomes == []
    db.refresh(record)
    assert record.status == AgentTaskStatus.WAITING_FOR_EXECUTION.value
    assert report_registry["generate_report"] == 0


# --- 7. Worker restart while WAITING -----------------------------------------


def test_worker_restart_claims_from_db_only(db, report_registry):
    """Simulates a fresh worker process after redeploy: new session claims."""
    _seed_exec(db, EXEC_A, ExecutionStatus.COMPLETED)
    record = _seed_waiting(db, [EXEC_A])
    db.expire_all()  # drop identity map: next reader is 'another process'

    fresh = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == record.task_id).first()
    outcome = resume_agent_task_core(
        db,
        fresh.task_id,
        event_type="ExecutionCompletedEvent",
        provider_factory=lambda _t: ReportOnResumeProvider(),
    )

    assert outcome == "COMPLETED"
    db.refresh(record)
    assert record.status == AgentTaskStatus.COMPLETED.value


# --- 8. Stale-WAITING recovery ------------------------------------------------


def test_stale_waiting_overdue_nonterminal_force_failed(db):
    from apps.backend.config import settings

    _seed_exec(db, EXEC_A, ExecutionStatus.RUNNING)
    waiting_since = datetime.now(UTC) - timedelta(
        seconds=settings.agent_execution_wait_deadline_seconds + 120
    )
    record = _seed_waiting(db, [EXEC_A], waiting_since=waiting_since)

    summary = recover_stale_waiting_tasks(db)

    assert summary["timed_out"] == 1
    db.refresh(record)
    assert record.status == AgentTaskStatus.FAILED.value
    assert record.snapshot["error_detail"].startswith("AGENT_RESUME_TIMEOUT")


def test_recent_waiting_with_inflight_runs_left_alone(db):
    _seed_exec(db, EXEC_A, ExecutionStatus.RUNNING)
    record = _seed_waiting(db, [EXEC_A])  # waiting_since = now

    summary = recover_stale_waiting_tasks(db)

    assert summary == {
        "resumed": 0,
        "timed_out": 0,
        "resume_failed": 0,
        "reaped_orphans": 0,
    }
    db.refresh(record)
    assert record.status == AgentTaskStatus.WAITING_FOR_EXECUTION.value


def test_orphaned_pending_row_reaped_after_window(db):
    """Pre-park orphans (serverless kill before any checkpoint) get failed."""
    record = _seed_waiting(db, [], status=AgentTaskStatus.PENDING.value)
    old = datetime.now(UTC) - timedelta(minutes=90)
    record.created_at = old
    record.updated_at = old
    db.commit()

    summary = recover_stale_waiting_tasks(db)

    assert summary["reaped_orphans"] == 1
    db.refresh(record)
    assert record.status == AgentTaskStatus.FAILED.value
    assert record.snapshot["error_detail"].startswith("AGENT_RESUME_TIMEOUT")


def test_fresh_executing_row_not_reaped(db):
    record = _seed_waiting(db, [], status=AgentTaskStatus.EXECUTING.value)
    recent = datetime.now(UTC) - timedelta(minutes=2)
    record.created_at = recent
    record.updated_at = recent
    db.commit()

    summary = recover_stale_waiting_tasks(db)

    assert summary["reaped_orphans"] == 0
    db.refresh(record)
    assert record.status == AgentTaskStatus.EXECUTING.value


def test_crashed_resumed_row_reclaimed_then_failed_at_limit(db):
    _seed_exec(db, EXEC_A, ExecutionStatus.COMPLETED)

    # Crashed resume: RESUMED row untouched past reclaim window.
    record = _seed_waiting(db, [EXEC_A], status=AgentTaskStatus.RESUMED.value, resume_count=1)
    record.updated_at = datetime.now(UTC) - timedelta(minutes=30)
    db.commit()

    summary1 = recover_stale_waiting_tasks(db)
    db.refresh(record)
    assert record.status in (
        AgentTaskStatus.WAITING_FOR_EXECUTION.value,
        AgentTaskStatus.COMPLETED.value,
    )

    if record.status == AgentTaskStatus.WAITING_FOR_EXECUTION.value:
        # Flip back to RESUMED at the attempt limit: recovery must fail it.
        record.status = AgentTaskStatus.RESUMED.value
        snap = dict(record.snapshot)
        snap["resume_count"] = MAX_RESUME_ATTEMPTS
        record.snapshot = snap
        record.updated_at = datetime.now(UTC) - timedelta(minutes=30)
        db.commit()
        summary2 = recover_stale_waiting_tasks(db)
        assert summary2["resume_failed"] == 1
        db.refresh(record)
        assert record.status == AgentTaskStatus.FAILED.value
        assert record.snapshot["error_detail"].startswith("AGENT_RESUME_FAILED")


# --- Subscriber wiring + park transition --------------------------------------


def test_subscriber_enqueues_only_terminal_execution_events(monkeypatch):
    from packages.execution_engine.domain.events import (
        ExecutionCompletedEvent,
        ExecutionQueuedEvent,
    )

    captured = []

    class FakeTask:
        @staticmethod
        def delay(*args):
            captured.append(args)

    import apps.backend.worker.agent_resume as mod

    monkeypatch.setattr(mod, "resume_agent_task", FakeTask)

    AgentTaskResumeSubscriber().handle(
        ExecutionCompletedEvent(
            timestamp=datetime.now(UTC),
            execution_id=uuid.UUID(EXEC_A),
            attempt_id=uuid.uuid4(),
        )
    )
    assert captured == [(EXEC_A, "ExecutionCompletedEvent", None)]

    # Non-terminal events are ignored entirely.
    AgentTaskResumeSubscriber().handle(
        ExecutionQueuedEvent(
            timestamp=datetime.now(UTC),
            execution_id=uuid.UUID(EXEC_A),
            benchmark_version_id=uuid.uuid4(),
            submitted_by=uuid.uuid4(),
        )
    )
    assert len(captured) == 1


def test_run_benchmark_dispatched_parks_task_by_default(report_registry, monkeypatch):
    """Default config parks on dispatch - no EXECUTION_BACKEND dependency."""
    from apps.backend.agent.agent import AtlasAgent
    from apps.backend.agent.tools.registry import ToolRegistry
    from apps.backend.config import settings

    # Explicitly ensure the default (no inline opt-out, any backend value).
    monkeypatch.setattr(settings, "agent_inline_execution_wait", False, raising=False)
    monkeypatch.setattr(settings, "execution_backend", "docker", raising=False)

    def fake_execute(self, tool_name=None, db=None, arguments=None, **kwargs):
        if tool_name == "run_benchmark":
            return {"status": "DISPATCHED", "execution_ids": [EXEC_A]}
        raise AssertionError(f"unexpected tool {tool_name}")

    monkeypatch.setattr(ToolRegistry, "execute", fake_execute)

    class DispatchProvider(BaseLLMProvider):
        def decide(self, task, context, declarations) -> AgentDecision:
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="run_benchmark",
                arguments={"benchmark_version_id": BENCHMARK_ID},
                reasoning="dispatch remote run",
            )

    class _NoopPlanner:
        def generate_initial_plan(self, goal, run_mode=None):
            return []

        def update_plan_on_decision(self, task, decision, output):
            return None

    task = AgentTask(goal="park me", primary_provider="test")
    agent = AtlasAgent(provider=DispatchProvider(), planner=_NoopPlanner())
    done = agent.run_task(task, db)

    assert done.status == AgentTaskStatus.WAITING_FOR_EXECUTION
    assert done.waiting_since is not None


def test_inline_execution_wait_opt_out_skips_park(monkeypatch, report_registry):
    """AGENT_INLINE_EXECUTION_WAIT=true restores the PR #54 inline wait."""
    from apps.backend.agent.agent import AtlasAgent
    from apps.backend.agent.tools.registry import ToolRegistry
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_inline_execution_wait", True, raising=False)

    def fake_execute(self, tool_name=None, db=None, arguments=None, **kwargs):
        if tool_name == "run_benchmark":
            return {"status": "DISPATCHED", "execution_ids": [EXEC_A]}
        if tool_name == "get_run_status":
            return {
                "execution_id": EXEC_A,
                "status": "COMPLETED",
                "progress": "100%",
            }
        raise AssertionError(f"unexpected tool {tool_name}")

    monkeypatch.setattr(ToolRegistry, "execute", fake_execute)

    class DispatchProvider(BaseLLMProvider):
        def __init__(self):
            self.dispatched = False

        def decide(self, task, context, declarations) -> AgentDecision:
            if self.dispatched:
                return AgentDecision(
                    type=AgentDecisionType.FAIL,
                    error_message="inline opt-out: end loop after dispatch",
                    reasoning="done",
                )
            self.dispatched = True
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="run_benchmark",
                arguments={"benchmark_version_id": BENCHMARK_ID},
                reasoning="dispatch remote run",
            )

    class _NoopPlanner:
        def generate_initial_plan(self, goal, run_mode=None):
            return []

        def update_plan_on_decision(self, task, decision, output):
            return None

    task = AgentTask(goal="inline wait", primary_provider="test")
    agent = AtlasAgent(provider=DispatchProvider(), planner=_NoopPlanner())
    done = agent.run_task(task, db)

    assert done.status != AgentTaskStatus.WAITING_FOR_EXECUTION
    assert done.waiting_since is None
    assert not any(t.event_type == "AGENT_TASK_WAITING" for t in done.execution_trace)
    assert done.execution_wait_started_at is not None
