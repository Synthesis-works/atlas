"""Tests for the GitHub Actions execution backend: validation, idempotency,
kill-switch routing, and dispatch failure policy."""

import uuid
from unittest.mock import Mock, patch

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from apps.backend.worker.github_dispatcher import (
    DuplicateDispatchError,
    ExecutionDispatchError,
    create_dispatch_attempt,
    dispatch_to_github,
    run_github_dispatch,
    validate_execution_id,
)
from atlas_db.core.base import Base
from atlas_db.models.execution import (
    AttemptStatus,
    Execution,
    ExecutionAttempt,
    ExecutionStatus,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    # Partial unique index (PostgreSQL syntax) - emulate on SQLite.
    import packages.execution_engine.persistence.models  # noqa: F401
    import atlas_db.models  # noqa: F401

    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_active_attempt_per_execution "
                "ON benchmark_execution_attempts(execution_id) "
                "WHERE status IN ('PENDING', 'CONTAINER_CREATED', 'RUNNING')"
            )
        )
        conn.commit()
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_queued_execution(db) -> Execution:
    execution = Execution(
        status=ExecutionStatus.QUEUED,
        target_model="mock",
        project_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
    )
    db.add(execution)
    db.commit()
    return execution


class TestValidateExecutionId:
    def test_accepts_valid_uuid(self):
        value = str(uuid.uuid4())
        assert validate_execution_id(value) == uuid.UUID(value)

    def test_rejects_injection_and_garbage(self):
        for bad in ["", None, "1; DROP TABLE users", "$(whoami)", "not-a-uuid"]:
            with pytest.raises(ExecutionDispatchError):
                validate_execution_id(bad)


class TestDispatchIdempotency:
    def test_creates_pending_attempt_for_queued_execution(self, db):
        execution = _make_queued_execution(db)
        attempt = create_dispatch_attempt(db, execution.id, "corr-1")
        assert attempt.status == AttemptStatus.PENDING
        assert attempt.executor_type == "github_actions"
        assert attempt.attempt_number == 1

    def test_second_active_attempt_is_rejected(self, db):
        execution = _make_queued_execution(db)
        create_dispatch_attempt(db, execution.id, "corr-1")
        db.commit()
        with pytest.raises(DuplicateDispatchError):
            create_dispatch_attempt(db, execution.id, "corr-2")

    def test_retry_allowed_after_terminal_attempt(self, db):
        execution = _make_queued_execution(db)
        first = create_dispatch_attempt(db, execution.id, "corr-1")
        first.status = AttemptStatus.FAILED
        db.commit()
        second = create_dispatch_attempt(db, execution.id, "corr-2")
        assert second.attempt_number == 2

    def test_non_queued_execution_is_rejected(self, db):
        execution = _make_queued_execution(db)
        execution.status = ExecutionStatus.RUNNING
        db.commit()
        with pytest.raises(ExecutionDispatchError, match="expected QUEUED"):
            create_dispatch_attempt(db, execution.id, "corr")


class TestGithubApiCall:
    def _transport(self, status_code: int) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code)

        return httpx.MockTransport(handler)

    def test_204_succeeds(self):
        dispatch_to_github(
            uuid.uuid4(),
            "corr",
            token="t",
            repo="o/r",
            event_type="benchmark-execution",
            transport=self._transport(204),
        )

    def test_non_204_raises_without_leaking_token(self):
        with pytest.raises(ExecutionDispatchError) as excinfo:
            dispatch_to_github(
                uuid.uuid4(),
                "corr",
                token="super-secret-token",
                repo="o/r",
                event_type="benchmark-execution",
                transport=self._transport(403),
            )
        assert "super-secret-token" not in str(excinfo.value)

    def test_payload_contains_only_identifiers(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["json"] = request.read().decode()
            return httpx.Response(204)

        eid = str(uuid.uuid4())
        dispatch_to_github(
            uuid.UUID(eid),
            "corr-9",
            token="t",
            repo="o/r",
            event_type="benchmark-execution",
            transport=httpx.MockTransport(handler),
        )
        assert eid in captured["json"]
        assert "corr-9" in captured["json"]
        assert "prompt" not in captured["json"].lower()

    def test_full_pipeline_commits_then_fires(self, db):
        execution = _make_queued_execution(db)
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            return httpx.Response(204)

        run_github_dispatch(
            db,
            str(execution.id),
            "corr-x",
            token="t",
            repo="o/r",
            event_type="benchmark-execution",
            transport=httpx.MockTransport(handler),
        )
        assert calls == ["/repos/o/r/dispatches"]
        attempt = db.query(ExecutionAttempt).one()
        assert attempt.executor_type == "github_actions"
