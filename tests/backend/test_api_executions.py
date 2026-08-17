import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from apps.backend.authz import require_permission
from apps.backend.main import app
from apps.backend.routers.executions import get_execution_service
from packages.execution_engine.api.dtos import (
    ExecutionAttemptResponse,
    ExecutionListResponse,
    ExecutionResponse,
)
from packages.execution_engine.application.execution_app_service import ExecutionApplicationService
from packages.execution_engine.domain.models import Execution, ExecutionState


@pytest.fixture
def mock_execution_service():
    return Mock(spec=ExecutionApplicationService)


@pytest.fixture
def test_client(mock_execution_service):
    from apps.backend.dependencies import get_db_session, require_authenticated
    from apps.backend.schemas.auth import TokenClaims

    mock_db = Mock()
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    app.dependency_overrides[get_execution_service] = lambda: mock_execution_service
    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[require_authenticated] = lambda: TokenClaims(
        sub=uuid.uuid4(), exp=9999999999, iat=1000000000, jti=uuid.uuid4()
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_execution(test_client, mock_execution_service):
    benchmark_id = uuid.uuid4()
    exec_id = uuid.uuid4()

    execution = Execution(
        id=exec_id, benchmark_version_id=benchmark_id, status=ExecutionState.QUEUED, max_retries=3
    )
    mock_execution_service.submit_execution.return_value = execution

    payload = {
        "benchmark_version_id": str(benchmark_id),
        "dataset_version_id": "00000000-0000-0000-0000-000000000006",
        "target_model": "groq/llama-3.1-8b-instant",
    }

    response = test_client.post(f"/api/v1/benchmarks/{benchmark_id}/executions", json=payload)

    assert response.status_code == 201
    assert response.json()["id"] == str(exec_id)
    assert response.json()["status"] == "QUEUED"


def test_list_executions(test_client):
    response = test_client.get("/api/v1/executions")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_cancel_execution(test_client, mock_execution_service):
    exec_id = uuid.uuid4()
    execution = Execution(
        id=exec_id,
        benchmark_version_id=uuid.uuid4(),
        status=ExecutionState.CANCELLED,
        max_retries=3,
    )
    mock_execution_service.cancel_execution.return_value = execution

    response = test_client.post(f"/api/v1/executions/{exec_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
