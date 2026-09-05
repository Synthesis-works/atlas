"""
Regression tests for the execution idempotency integrity path (Finding 8).

When two dispatch requests carrying the same idempotency key race, the database
partial unique index lets only one insert commit. The loser must roll back and
resolve to the already-committed execution rather than erroring out or queuing a
duplicate.
"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from packages.execution_engine.application.execution_app_service import (
    ExecutionApplicationService,
)
from packages.execution_engine.domain.models import Execution, ExecutionState


def make_execution(exec_id: uuid.UUID):
    return Execution.rehydrate(
        id=exec_id,
        benchmark_version_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=ExecutionState.QUEUED,
        created_by=uuid.uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        max_retries=3,
        attempts=[],
    )


class FakeDomainService:
    def __init__(self):
        self.created = []

    def create_execution(self, **kwargs):
        execution = make_execution(kwargs["execution_id"])
        self.created.append(execution)
        return execution


class RacingSession:
    """A session that fails the commit once (unique index collision)."""

    def __init__(self, existing_row, fail_commits=1):
        self.existing_row = existing_row
        self.commit_calls = 0
        self.rollback_calls = 0
        self.fail_commits = fail_commits

    def add(self, *args, **kwargs):
        return None

    def commit(self):
        self.commit_calls += 1
        if self.commit_calls <= self.fail_commits:
            raise IntegrityError("INSERT INTO executions ...", {}, Exception("duplicate key"))

    def rollback(self):
        self.rollback_calls += 1

    def query(self, *args, **kwargs):
        return SimpleNamespace(
            filter=lambda *a, **k: SimpleNamespace(first=lambda: self.existing_row)
        )


class FakeExecutionRepo:
    def __init__(self, session, existing_domain):
        self.session = session
        self.existing_domain = existing_domain

    def save(self, execution) -> None:
        self.session.add(execution)

    def get(self, execution_id: uuid.UUID) -> Execution | None:
        return self.existing_domain


class FakeBenchmarkRepo:
    def __init__(self, project_id: uuid.UUID):
        self._project_id = project_id
        self.db = SimpleNamespace(
            query=lambda *a, **k: SimpleNamespace(
                get=lambda *a2, **k2: SimpleNamespace(
                    benchmark=SimpleNamespace(project_id=self._project_id)
                )
            )
        )


def test_submit_execution_duplicate_race_resolves_to_existing_execution():
    existing_id = uuid.uuid4()
    existing_domain = make_execution(existing_id)
    existing_row = SimpleNamespace(id=existing_id)
    session = RacingSession(existing_row)
    repo = FakeExecutionRepo(session, existing_domain)

    service = ExecutionApplicationService(
        domain_service=FakeDomainService(),
        execution_repo=repo,
        benchmark_repo=FakeBenchmarkRepo(uuid.uuid4()),
    )

    result = service.submit_execution(
        benchmark_version_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        submitted_by=uuid.uuid4(),
        target_model="mock",
        idempotency_key="shared-submission-key",
    )

    assert result.id == existing_id
    assert session.commit_calls == 1
    assert session.rollback_calls == 1


def test_submit_execution_without_key_reraises_integrity_error():
    existing_row = SimpleNamespace(id=uuid.uuid4())
    session = RacingSession(existing_row)
    repo = FakeExecutionRepo(session, make_execution(uuid.uuid4()))

    service = ExecutionApplicationService(
        domain_service=FakeDomainService(),
        execution_repo=repo,
        benchmark_repo=FakeBenchmarkRepo(uuid.uuid4()),
    )

    with pytest.raises(IntegrityError):
        service.submit_execution(
            benchmark_version_id=uuid.uuid4(),
            dataset_version_id=uuid.uuid4(),
            submitted_by=uuid.uuid4(),
            target_model="mock",
        )


def test_submit_execution_stores_idempotency_key_on_db_execution_row():
    class RecordingSession(RacingSession):
        def __init__(self):
            super().__init__(SimpleNamespace(id=uuid.uuid4()), fail_commits=0)
            self.added_rows = []

        def add(self, row, *args, **kwargs):
            self.added_rows.append(row)
            return None

    session = RecordingSession()
    repo = FakeExecutionRepo(session, make_execution(uuid.uuid4()))

    service = ExecutionApplicationService(
        domain_service=FakeDomainService(),
        execution_repo=repo,
        benchmark_repo=FakeBenchmarkRepo(uuid.uuid4()),
    )

    service.submit_execution(
        benchmark_version_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        submitted_by=uuid.uuid4(),
        target_model="mock",
        idempotency_key="key-on-row",
    )

    assert len(session.added_rows) >= 2  # domain model + DBExecution row
    db_row = session.added_rows[-1]
    assert db_row.idempotency_key == "key-on-row"
