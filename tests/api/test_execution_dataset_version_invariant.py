"""
Regression tests for the execution dataset_version_id invariant (Finding 2).

Dispatch must never fabricate a dataset version. Previously an arbitrary
TestCase.dataset_version_id (from ANY benchmark) or a random UUID was silently
attached when the benchmark version declared no primary dataset version, and a
caller-supplied foreign dataset version was accepted. Now unknown, missing, or
unassociated dataset versions are rejected, and dispatch targets surface an
unconfigured version as empty instead of inventing a dataset.
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


class FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return self._result


def make_dv(dv_id: uuid.UUID):
    return SimpleNamespace(id=dv_id)


def make_version(*, primary=None, linked=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        benchmark_id=uuid.uuid4(),
        primary_dataset_version_id=primary,
        dataset_versions=[make_dv(d) for d in (linked or [])],
    )


@pytest.fixture
def dispatch_env():
    """Overrides auth + db access; returns helpers to control responses."""
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )

    def mock_submit_execution(*args, **kwargs):
        return Execution.rehydrate(
            id=uuid.uuid4(),
            benchmark_version_id=kwargs.get("benchmark_version_id", uuid.uuid4()),
            project_id=uuid.uuid4(),
            status=ExecutionState.QUEUED,
            created_by=user_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            max_retries=3,
            attempts=[],
        )

    mock_service = MagicMock()
    mock_service.submit_execution.side_effect = mock_submit_execution

    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_execution_service] = lambda: mock_service

    def set_query_result(result):
        fake_db = MagicMock()
        fake_db.query.return_value = FakeQuery(result)
        app.dependency_overrides[get_db_session] = lambda: fake_db

    yield {"set_query_result": set_query_result, "mock_claims": mock_claims}

    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_execution_service, None)
    app.dependency_overrides.pop(get_db_session, None)


def test_dispatch_without_any_dataset_version_is_rejected(dispatch_env):
    """No primary and no provided dataset_version_id -> 422, never a fabricated UUID."""
    bv = make_version(primary=None, linked=[])
    dispatch_env["set_query_result"](bv)

    res = client.post(f"/api/v1/benchmarks/{bv.id}/executions", json={"target_model": "mock"})
    assert res.status_code == 422
    assert "dataset_version_id" in res.json()["error"]["message"]


def test_dispatch_with_unassociated_dataset_version_is_rejected(dispatch_env):
    """A dataset version the benchmark version does not link to -> 422."""
    bv = make_version(primary=None, linked=[uuid.uuid4()])
    foreign_dv = uuid.uuid4()
    dispatch_env["set_query_result"](bv)

    res = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={"target_model": "mock", "dataset_version_id": str(foreign_dv)},
    )
    assert res.status_code == 422
    assert "not associated" in res.json()["error"]["message"]


def test_dispatch_with_invalid_dataset_version_uuid_is_rejected(dispatch_env):
    bv = make_version(primary=None, linked=[])
    dispatch_env["set_query_result"](bv)

    res = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={"target_model": "mock", "dataset_version_id": "not-a-uuid"},
    )
    assert res.status_code == 422


def test_dispatch_with_linked_dataset_version_succeeds(dispatch_env):
    linked_dv = uuid.uuid4()
    bv = make_version(primary=None, linked=[linked_dv])
    dispatch_env["set_query_result"](bv)

    res = client.post(
        f"/api/v1/benchmarks/{bv.id}/executions",
        json={"target_model": "mock", "dataset_version_id": str(linked_dv)},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "QUEUED"


def test_dispatch_missing_token_subject_is_rejected(dispatch_env):
    """A non-UUID token subject must yield 401 rather than a randomized user id."""
    from fastapi import HTTPException

    from apps.backend.routers.executions import create_execution
    from packages.execution_engine.api.dtos import ExecutionCreateRequest

    bv = make_version(primary=uuid.uuid4(), linked=[uuid.uuid4()])
    fake_db = MagicMock()
    fake_db.query.return_value = FakeQuery(bv)
    service = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        create_execution(
            bv.id,
            payload=ExecutionCreateRequest(target_model="mock"),
            db=fake_db,
            service=service,
            current_user={"sub": "not-a-uuid"},
        )
    assert exc_info.value.status_code == 401
    service.submit_execution.assert_not_called()


def test_dispatch_targets_leave_unconfigured_dataset_empty(dispatch_env):
    """Dispatch targets must not attach an arbitrary dataset to an unconfigured version."""
    bv_with_dv = uuid.uuid4()
    dv_id = uuid.uuid4()
    bv_without_dv = uuid.uuid4()
    rows = [
        (bv_with_dv, "Configured Benchmark", "1.0.0", dv_id),
        (bv_without_dv, "Unconfigured Benchmark", "1.0.0", None),
    ]
    dispatch_env["set_query_result"](rows)

    res = client.get("/api/v1/executions/dispatch-targets")
    assert res.status_code == 200
    targets = res.json()

    configured = next(t for t in targets if t["benchmark_version_id"] == str(bv_with_dv))
    assert configured["dataset_version_id"] == str(dv_id)

    unconfigured = next(t for t in targets if t["benchmark_version_id"] == str(bv_without_dv))
    assert unconfigured["dataset_version_id"] is None
