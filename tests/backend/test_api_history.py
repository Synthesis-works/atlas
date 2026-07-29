import uuid
from datetime import datetime, timezone, UTC
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from apps.backend.dependencies import get_execution_app_service, require_authenticated
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.executions import ExecutionHistoryRead, ModelActivityRead


@pytest.fixture
def mock_execution_app_service():
    return Mock()


@pytest.fixture
def test_client(mock_execution_app_service):
    app.dependency_overrides[get_execution_app_service] = lambda: mock_execution_app_service

    def override_claims():
        return TokenClaims(
            sub=uuid.uuid4(),
            exp=9999999999,
            iat=1000000000,
            jti=uuid.uuid4(),
        )

    app.dependency_overrides[require_authenticated] = override_claims
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_recent_executions(test_client, mock_execution_app_service):
    """Test getting recent executions history"""
    now = datetime.now(UTC)

    exec1 = ExecutionHistoryRead(
        id=uuid.uuid4(),
        benchmark_name="Math Benchmark",
        target_model="gpt-4",
        status="COMPLETED",
        started_at=now,
        completed_at=now,
        duration=1000,
        project_id=uuid.uuid4(),
    )

    exec2 = ExecutionHistoryRead(
        id=uuid.uuid4(),
        benchmark_name="Coding Benchmark",
        target_model="claude-3-opus",
        status="RUNNING",
        started_at=now,
        completed_at=None,
        duration=None,
        project_id=uuid.uuid4(),
    )

    # Simulate service returning newest first
    mock_execution_app_service.get_recent_executions.return_value = [exec1, exec2]

    response = test_client.get("/api/v1/history/executions/recent?limit=10")

    assert response.status_code == 200
    data = response.json()["data"]

    assert len(data) == 2
    assert data[0]["benchmark_name"] == "Math Benchmark"
    assert data[1]["benchmark_name"] == "Coding Benchmark"
    assert data[0]["target_model"] == "gpt-4"
    assert data[1]["target_model"] == "claude-3-opus"

    mock_execution_app_service.get_recent_executions.assert_called_once_with(limit=10)


def test_list_recent_models(test_client, mock_execution_app_service):
    """Test getting recent models history"""
    now = datetime.now(UTC)

    model1 = ModelActivityRead(name="gpt-4", last_executed_at=now, execution_count=150)

    model2 = ModelActivityRead(name="claude-3-opus", last_executed_at=now, execution_count=83)

    # Simulate service returning newest first
    mock_execution_app_service.get_recent_models.return_value = [model1, model2]

    response = test_client.get("/api/v1/history/models/recent?limit=5")

    assert response.status_code == 200
    data = response.json()["data"]

    assert len(data) == 2
    assert data[0]["name"] == "gpt-4"
    assert data[0]["execution_count"] == 150
    assert data[1]["name"] == "claude-3-opus"
    assert data[1]["execution_count"] == 83

    mock_execution_app_service.get_recent_models.assert_called_once_with(limit=5)
