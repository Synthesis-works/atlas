import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.main import app
from apps.backend.routers.executions import get_execution_service
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.authoring import BenchmarkVersion
from packages.execution_engine.application.execution_app_service import ExecutionApplicationService
from packages.execution_engine.domain.exceptions import ExecutionNotFoundError
from packages.execution_engine.domain.models import Execution, ExecutionState

# These tests exercise the API route that reads the authoritative atlas_db
# ``executions`` mapper; mixing with the ee persistence Base (test_persistence)
# corrupts the shared mapper registry, so this file must run in isolation too.
pytestmark = pytest.mark.isolate

client = TestClient(app)


def mock_require_authenticated():
    return TokenClaims(
        sub=uuid.uuid4(),
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )


@pytest.fixture(autouse=True)
def apply_dependency_overrides():
    app.dependency_overrides[require_authenticated] = mock_require_authenticated
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_exec_service():
    service = MagicMock(spec=ExecutionApplicationService)
    app.dependency_overrides[get_execution_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_execution_service, None)


def test_create_execution(mock_exec_service):
    bv_id = uuid.uuid4()
    benchmark_version = BenchmarkVersion(
        id=bv_id,
        benchmark_id=uuid.uuid4(),
        version_string="v1",
        primary_dataset_version_id=uuid.uuid4(),
    )
    db = MagicMock()
    benchmark_row = MagicMock()
    benchmark_row.status = "published"
    benchmark_row.project_id = uuid.uuid4()
    db.query.return_value.filter.return_value.first.side_effect = [benchmark_version, benchmark_row]
    app.dependency_overrides[get_db_session] = lambda: db

    mock_execution = Execution(
        id=uuid.uuid4(),
        benchmark_version_id=bv_id,
        status=ExecutionState.QUEUED,
    )
    mock_exec_service.submit_execution.return_value = mock_execution

    response = client.post(f"/api/v1/benchmarks/{bv_id}/executions")

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "QUEUED"
    assert data["benchmark_version_id"] == str(bv_id)
    assert mock_exec_service.submit_execution.called
    app.dependency_overrides.pop(get_db_session, None)


def test_get_execution(mock_exec_service):
    exec_id = uuid.uuid4()
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
    from atlas_db.models.execution import Execution as DBExecution, ExecutionStatus

    row = DBExecution(
        id=exec_id,
        project_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        submitted_by_id=uuid.uuid4(),
        target_model="mock",
        status=ExecutionStatus.RUNNING,
        total_items=10,
        completed_items=3,
        queued_at=now,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = row
    app.dependency_overrides[get_db_session] = lambda: db

    response = client.get(f"/api/v1/executions/{exec_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(exec_id)
    assert body["status"] == "RUNNING"
    assert body["completed_items"] == 3
    assert body["completed_at"] is None
    # The read path is fully authoritative — the engine aggregate is never consulted.
    mock_exec_service.get_execution.assert_not_called()
    app.dependency_overrides.pop(get_db_session, None)


def test_cancel_execution(mock_exec_service):
    exec_id = uuid.uuid4()
    mock_execution = Execution(
        id=exec_id,
        benchmark_version_id=uuid.uuid4(),
        status=ExecutionState.CANCELLING,
    )
    mock_exec_service.cancel_execution.return_value = mock_execution

    response = client.post(f"/api/v1/executions/{exec_id}/cancel")

    assert response.status_code == 200
    assert response.json()["id"] == str(exec_id)
    assert response.json()["status"] == "CANCELLING"
    assert mock_exec_service.cancel_execution.called


def test_cancel_execution_not_found(mock_exec_service):
    exec_id = uuid.uuid4()
    mock_exec_service.cancel_execution.side_effect = ExecutionNotFoundError("Execution not found")

    response = client.post(f"/api/v1/executions/{exec_id}/cancel")

    assert response.status_code == 404
