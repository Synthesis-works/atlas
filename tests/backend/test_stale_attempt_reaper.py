"""Unit tests for the stale-attempt reaper (SQLite, no Docker required)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from atlas_db.models.execution import (
    AttemptStatus,
    Execution,
    ExecutionAttempt,
    ExecutionStatus,
)
from apps.backend.worker.stale_attempt_reaper import reap_stale_attempts


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        yield session


def _make_execution(status: ExecutionStatus = ExecutionStatus.RUNNING) -> Execution:
    return Execution(
        id=uuid.uuid4(),
        status=status,
        target_model="mock",
        project_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
    )


def _make_attempt(
    db,
    execution: Execution,
    status: AttemptStatus,
    age_minutes: int,
    trace_id: str | None = None,
) -> ExecutionAttempt:
    now = datetime.now(UTC)
    attempt = ExecutionAttempt(
        id=uuid.uuid4(),
        execution_id=execution.id,
        attempt_number=1,
        status=status,
        executor_type="docker",
        trace_id=trace_id,
    )
    db.add(attempt)
    db.flush()
    # Backdate updated_at directly (onupdate would otherwise refresh it).
    db.execute(
        ExecutionAttempt.__table__.update()
        .where(ExecutionAttempt.__table__.c.id == attempt.id)
        .values(updated_at=now - timedelta(minutes=age_minutes))
    )
    return attempt


class TestReapStaleAttempts:
    def test_reaps_old_running_attempt_and_requeues_execution(self, db_session):
        execution = _make_execution(status=ExecutionStatus.RUNNING)
        db_session.add(execution)
        attempt = _make_attempt(db_session, execution, AttemptStatus.RUNNING, age_minutes=60)
        db_session.commit()

        summary = reap_stale_attempts(db_session, max_age_minutes=45)

        assert summary == {"attempts_reaped": 1, "executions_requeued": 1}
        db_session.refresh(attempt)
        db_session.refresh(execution)
        assert attempt.status == AttemptStatus.FAILED
        assert attempt.termination_reason == "runner_restarted"
        assert attempt.finished_at is not None
        assert execution.status == ExecutionStatus.QUEUED

    def test_ignores_recent_attempts(self, db_session):
        execution = _make_execution(status=ExecutionStatus.RUNNING)
        db_session.add(execution)
        attempt = _make_attempt(db_session, execution, AttemptStatus.RUNNING, age_minutes=10)
        db_session.commit()

        summary = reap_stale_attempts(db_session, max_age_minutes=45)

        assert summary == {"attempts_reaped": 0, "executions_requeued": 0}
        db_session.refresh(attempt)
        assert attempt.status == AttemptStatus.RUNNING

    def test_ignores_terminal_attempts(self, db_session):
        execution = _make_execution(status=ExecutionStatus.COMPLETED)
        db_session.add(execution)
        attempt = _make_attempt(db_session, execution, AttemptStatus.COMPLETED, age_minutes=500)
        db_session.commit()

        summary = reap_stale_attempts(db_session, max_age_minutes=45)

        assert summary == {"attempts_reaped": 0, "executions_requeued": 0}

    def test_does_not_requeue_terminal_executions(self, db_session):
        execution = _make_execution(status=ExecutionStatus.COMPLETED)
        db_session.add(execution)
        _make_attempt(db_session, execution, AttemptStatus.RUNNING, age_minutes=90)
        db_session.commit()

        summary = reap_stale_attempts(db_session, max_age_minutes=45)

        assert summary["attempts_reaped"] == 1
        assert summary["executions_requeued"] == 0
        db_session.refresh(execution)
        assert execution.status == ExecutionStatus.COMPLETED

    def test_reaps_pending_and_container_created_states(self, db_session):
        execution_a = _make_execution(status=ExecutionStatus.STARTING)
        execution_b = _make_execution(status=ExecutionStatus.RUNNING)
        db_session.add_all([execution_a, execution_b])
        _make_attempt(db_session, execution_a, AttemptStatus.PENDING, age_minutes=120)
        _make_attempt(db_session, execution_b, AttemptStatus.CONTAINER_CREATED, age_minutes=120)
        db_session.commit()

        summary = reap_stale_attempts(db_session, max_age_minutes=45)

        assert summary == {"attempts_reaped": 2, "executions_requeued": 2}


class TestReaperSafetyInvariants:
    def test_default_window_exceeds_max_attempt_runtime(self):
        """H-2: reap cutoff must never be reachable by a legitimately running attempt."""
        from apps.backend.worker.stale_attempt_reaper import (
            DEFAULT_REAP_AFTER_MINUTES,
            MAX_ATTEMPT_RUNTIME_MINUTES,
        )

        assert DEFAULT_REAP_AFTER_MINUTES > MAX_ATTEMPT_RUNTIME_MINUTES
        # Celery hard kill is 61 min; the default window must clear it with margin.
        assert DEFAULT_REAP_AFTER_MINUTES >= 90

    def test_recent_attempt_beyond_old_45min_window_survives_default(self, db_session):
        """A 50-minute attempt is legitimate under celery's 61-min hard limit."""
        execution = _make_execution(status=ExecutionStatus.RUNNING)
        db_session.add(execution)
        attempt = _make_attempt(db_session, execution, AttemptStatus.RUNNING, age_minutes=50)
        db_session.commit()

        summary = reap_stale_attempts(db_session)  # default window

        assert summary == {"attempts_reaped": 0, "executions_requeued": 0}
        db_session.refresh(attempt)
        assert attempt.status == AttemptStatus.RUNNING


class TestRequeueEmitsOutboxEvent:
    def test_requeued_execution_gets_outbox_row_same_transaction(self, db_session):
        """H-4: a bare status flip strands executions; an outbox row must exist."""
        from atlas_db.models.outbox import OutboxMessage

        execution = _make_execution(status=ExecutionStatus.RUNNING)
        db_session.add(execution)
        attempt = _make_attempt(
            db_session, execution, AttemptStatus.RUNNING, age_minutes=200, trace_id="trace-abc"
        )
        db_session.commit()

        summary = reap_stale_attempts(db_session, max_age_minutes=120)

        assert summary["executions_requeued"] == 1
        rows = db_session.query(OutboxMessage).all()
        assert len(rows) == 1
        msg = rows[0]
        assert msg.event_type == "ExecutionQueuedEvent"
        assert msg.aggregate_id == execution.id
        assert msg.payload == {"execution_id": str(execution.id)}
        assert msg.trace_context["correlation_id"] == "trace-abc"

    def test_no_outbox_row_when_execution_not_requeued(self, db_session):
        from atlas_db.models.outbox import OutboxMessage

        execution = _make_execution(status=ExecutionStatus.COMPLETED)
        db_session.add(execution)
        _make_attempt(db_session, execution, AttemptStatus.RUNNING, age_minutes=200)
        db_session.commit()

        reap_stale_attempts(db_session, max_age_minutes=120)

        assert db_session.query(OutboxMessage).count() == 0
