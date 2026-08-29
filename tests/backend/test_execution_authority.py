"""Regression tests: GET /api/v1/executions/{id} must read the authoritative
``executions`` table row — the same record reports/listing/dashboard consume.

Guards against the historical drift where ``run get`` surfaced the engine's
internal ``ee_executions`` aggregate (QUEUED/RUNNING forever, null timestamps)
while every other surface showed a terminal, truthful state.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Generator
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.main import app
from apps.backend.routers.executions import get_execution_service
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.execution import Execution as DBExecution, ExecutionStatus
from packages.execution_engine.application.execution_app_service import ExecutionApplicationService
from packages.execution_engine.domain.models import Execution, ExecutionState

_UTC_FIXED = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


def _authoritative_row(
    *,
    execution_id: uuid.UUID,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
    target_model: str = "mock",
    completed_items: int = 10,
    total_items: int = 10,
    started_at: datetime = _UTC_FIXED,
    completed_at: datetime | None = _UTC_FIXED,
) -> DBExecution:
    """Construct an in-memory authoritative ``executions`` row (no DB touch)."""
    return DBExecution(
        id=execution_id,
        project_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        benchmark_version_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        dataset_version_id=uuid.UUID("00000000-0000-0000-0000-000000000006"),
        submitted_by_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        target_model=target_model,
        status=status,
        total_items=total_items,
        completed_items=completed_items,
        queued_at=started_at,
        started_at=started_at,
        completed_at=completed_at,
        created_at=started_at,
        updated_at=completed_at or started_at,
    )


def _configure_db_for_row(db: MagicMock, row: DBExecution) -> None:
    """Wire the db mock so the route's get path and list path resolve ``row``."""
    db.query.return_value.filter.return_value.first.return_value = row
    db.query.return_value.count.return_value = 1
    db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [row]


@pytest.fixture
def db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def engine_service() -> Mock:
    """Engine-side service whose aggregate is parked at RUNNING (the historical drift)."""
    service = Mock(spec=ExecutionApplicationService)
    service.get_execution.return_value = Execution(
        id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        status=ExecutionState.RUNNING,
        max_retries=3,
    )
    return service


@pytest.fixture
def test_client(db: MagicMock, engine_service: Mock) -> Generator[TestClient, None, None]:
    """TestClient with auth + engine overridden; db mock shared across the app."""
    app.dependency_overrides[get_execution_service] = lambda: engine_service
    app.dependency_overrides[get_db_session] = lambda: db
    app.dependency_overrides[require_authenticated] = lambda: TokenClaims(
        sub=uuid.uuid4(), exp=9999999999, iat=1000000000, jti=uuid.uuid4()
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def execution_id() -> uuid.UUID:
    return uuid.uuid4()


def test_get_execution_reads_authoritative_row_not_engine_aggregate(
    test_client: TestClient,
    engine_service: Mock,
    db: MagicMock,
    execution_id: uuid.UUID,
) -> None:
    """Engine may still hold RUNNING for the same id; the endpoint must report the
    authoritative terminal row and never consult the engine on reads."""
    row = _authoritative_row(execution_id=execution_id)
    _configure_db_for_row(db, row)

    response = test_client.get(f"/api/v1/executions/{execution_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(execution_id)
    assert body["status"] == "COMPLETED"
    assert body["completed_items"] == 10
    assert body["total_items"] == 10
    assert body["started_at"] == _UTC_FIXED.isoformat().replace("+00:00", "Z")
    assert body["completed_at"] == _UTC_FIXED.isoformat().replace("+00:00", "Z")
    assert body["target_model"] == "mock"
    assert body["attempts"] == []
    engine_service.get_execution.assert_not_called()


def test_get_execution_matches_list_surface(
    test_client: TestClient,
    db: MagicMock,
    execution_id: uuid.UUID,
) -> None:
    """The single-execution read and the list surface (both authoritative) must agree
    field-for-field — this is the 'cannot drift' invariant across surfaces."""
    row = _authoritative_row(execution_id=execution_id)
    _configure_db_for_row(db, row)

    single = test_client.get(f"/api/v1/executions/{execution_id}").json()
    listed = test_client.get("/api/v1/executions").json()["items"][0]

    keys = {
        "id",
        "benchmark_version_id",
        "status",
        "target_model",
        "completed_items",
        "total_items",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
        "created_by",
        "max_retries",
        "attempts",
    }
    assert {k: single[k] for k in keys} == {k: listed[k] for k in keys}


def test_get_execution_surfaces_truthful_partial_progress(
    test_client: TestClient,
    db: MagicMock,
    execution_id: uuid.UUID,
) -> None:
    """An in-flight authoritative row reports its real timestamps and progress,
    never the engine aggregate's null started_at."""
    row = _authoritative_row(
        execution_id=execution_id,
        status=ExecutionStatus.RUNNING,
        completed_items=3,
        total_items=10,
        completed_at=None,
    )
    _configure_db_for_row(db, row)

    body = test_client.get(f"/api/v1/executions/{execution_id}").json()

    assert body["status"] == "RUNNING"
    assert body["started_at"] == _UTC_FIXED.isoformat().replace("+00:00", "Z")
    assert body["completed_at"] is None
    assert body["completed_items"] == 3
    assert body["total_items"] == 10


def test_get_execution_404_when_authoritative_row_missing(
    test_client: TestClient,
    db: MagicMock,
    execution_id: uuid.UUID,
) -> None:
    """Missing authoritative row still yields a clean 404, never an engine fallback."""
    db.query.return_value.filter.return_value.first.return_value = None

    response = test_client.get(f"/api/v1/executions/{execution_id}")

    body = response.json()
    assert response.status_code == 404
    assert body["error"]["code"] == "HTTP_404"
    assert body["error"]["message"] == "Execution not found"
