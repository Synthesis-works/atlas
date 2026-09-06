"""
Regression tests for execution idempotency (Finding 8).

Repeated or concurrently replayed dispatch requests carrying the same
`idempotency_key` must resolve to a single execution record. Sequential
duplicates are absorbed by the router pre-check; a lost race is caught at the
database unique index and resolved inside the application service.
"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.routers.executions import get_execution_service
from packages.execution_engine.domain.models import Execution, ExecutionState

client = TestClient(app)


def make_version(*, primary=None, linked=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        benchmark_id=uuid.uuid4(),
        primary_dataset_version_id=primary,
        dataset_versions=[SimpleNamespace(id=d) for d in (linked or [])],
    )


def make_execution(exec_id: uuid.UUID, *, benchmark_version_id, project_id, user_id):
    return Execution.rehydrate(
        id=exec_id,
        benchmark_version_id=benchmark_version_id,
        project_id=project_id,
        status=ExecutionState.QUEUED,
        created_by=user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        max_retries=3,
        attempts=[],
    )


def make_db_row(db_exec_id: uuid.UUID, bv_id: uuid.UUID, user_id: uuid.UUID):
    return SimpleNamespace(
        id=db_exec_id,
        benchmark_version_id=bv_id,
        status="QUEUED",
        target_model="mock",
        completed_items=0,
        total_items=1,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        submitted_by_id=user_id,
        max_retries=3,
    )


class IdempotentQuery:
    """Returns the benchmark version for the first lookup, then the idempotency row."""

    def __init__(self, db):
        self.db = db

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        if self.db.idem_fetched:
            return self.db.idem_row
        self.db.idem_fetched = True
        return self.db.version

    def all(self):
        return []


class IdempotentDb:
    def __init__(self, version, idem_row=None):
        self.version = version
        self.idem_row = idem_row
        self.idem_fetched = False

    def query(self, *args, **kwargs):
        return IdempotentQuery(self)


@pytest.fixture
def idempotency_env():
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )
    submitted = []

    def mock_submit_execution(*args, **kwargs):
        exec_id = uuid.uuid4()
        submitted.append(exec_id)
        return make_execution(
            exec_id,
            benchmark_version_id=kwargs.get("benchmark_version_id", uuid.uuid4()),
            project_id=uuid.uuid4(),
            user_id=user_id,
        )

    mock_service = MagicMock()
    mock_service.submit_execution.side_effect = mock_submit_execution
    state = {"idem_row": None, "version": None}

    def set_db(version):
        # Each request receives a fresh IdempotentDb so the version lookup is
        # the first .first() of every request, while the resolvable idempotency
        # row (if any) lives in shared state that the test can update.
        state["version"] = version
        app.dependency_overrides[get_db_session] = lambda: IdempotentDb(
            state["version"], idem_row=state["idem_row"]
        )

    def set_idem_row(row):
        state["idem_row"] = row

    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_execution_service] = lambda: mock_service

    yield {
        "set_db": set_db,
        "set_idem_row": set_idem_row,
        "submitted": submitted,
        "mock_service": mock_service,
        "user_id": user_id,
    }

    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_execution_service, None)
    app.dependency_overrides.pop(get_db_session, None)


def test_repeated_submission_with_same_idempotency_key_resolves_to_same_execution(
    idempotency_env,
):
    bv = make_version(primary=None, linked=[uuid.uuid4()])
    dv_id = bv.dataset_versions[0].id
    idempotency_env["set_db"](bv)

    first = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={
            "target_model": "mock",
            "dataset_version_id": str(dv_id),
            "idempotency_key": "dispatch-round-1",
        },
    )
    assert first.status_code == 201
    created_id = first.json()["id"]

    # A subsequent replay carries the same key; the router resolves to the
    # committed execution and must NOT submit a second time.
    row = make_db_row(uuid.UUID(created_id), bv.id, idempotency_env["user_id"])
    idempotency_env["set_idem_row"](row)

    replay = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={
            "target_model": "mock",
            "dataset_version_id": str(dv_id),
            "idempotency_key": "dispatch-round-1",
        },
    )
    # The route reports 201 for an accepted submission; the idempotency
    # contract is that the replay resolves to the SAME execution record.
    assert replay.status_code == 201
    assert replay.json()["id"] == created_id
    assert len(idempotency_env["submitted"]) == 1
    idempotency_env["mock_service"].submit_execution.assert_called_once()


def test_distinct_idempotency_keys_produce_distinct_executions(idempotency_env):
    bv = make_version(primary=None, linked=[uuid.uuid4()])
    dv_id = bv.dataset_versions[0].id
    idempotency_env["set_db"](bv)

    first = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={"target_model": "mock", "dataset_version_id": str(dv_id), "idempotency_key": "key-a"},
    )
    second = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={"target_model": "mock", "dataset_version_id": str(dv_id), "idempotency_key": "key-b"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert len(idempotency_env["submitted"]) == 2


def test_no_idempotency_key_skips_dedup_lookup(idempotency_env):
    bv = make_version(primary=None, linked=[uuid.uuid4()])
    dv_id = bv.dataset_versions[0].id
    idempotency_env["set_db"](bv)

    first = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={"target_model": "mock", "dataset_version_id": str(dv_id)},
    )
    second = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={"target_model": "mock", "dataset_version_id": str(dv_id)},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
