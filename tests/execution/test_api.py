import pytest
from fastapi.testclient import TestClient
import uuid
from typing import Any
from unittest.mock import MagicMock

from apps.backend.main import app
from apps.backend.dependencies import get_current_user
from packages.execution_engine.application.execution_app_service import ExecutionApplicationService
from apps.backend.routers.executions import get_execution_service

client = TestClient(app)

def mock_get_current_user():
    return {"user_id": uuid.uuid4(), "permissions": ["benchmark:execute", "execution:read", "execution:cancel"]}

app.dependency_overrides[get_current_user] = mock_get_current_user

@pytest.fixture
def mock_exec_service():
    service = MagicMock(spec=ExecutionApplicationService)
    app.dependency_overrides[get_execution_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_execution_service, None)

def test_create_execution(mock_exec_service):
    bv_id = uuid.uuid4()
    
    mock_execution = MagicMock()
    mock_execution.id = uuid.uuid4()
    mock_execution.benchmark_version_id = bv_id
    mock_execution.status.value = "QUEUED"
    mock_execution.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"
    mock_execution.updated_at.isoformat.return_value = "2023-01-01T00:00:00Z"
    mock_execution.created_by = uuid.uuid4()
    mock_execution.max_retries = 3
    mock_execution.attempts = []
    
    mock_exec_service.submit_execution.return_value = mock_execution
    
    response = client.post(f"/api/v1/benchmarks/{bv_id}/executions")
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "QUEUED"
    assert data["benchmark_version_id"] == str(bv_id)
    assert mock_exec_service.submit_execution.called

def test_get_execution(mock_exec_service):
    exec_id = uuid.uuid4()
    
    mock_execution = MagicMock()
    mock_execution.id = exec_id
    mock_execution.benchmark_version_id = uuid.uuid4()
    mock_execution.status.value = "RUNNING"
    mock_execution.attempts = []
    
    mock_exec_service.get_execution.return_value = mock_execution
    
    response = client.get(f"/api/v1/executions/{exec_id}")
    
    assert response.status_code == 200
    assert response.json()["id"] == str(exec_id)
    assert mock_exec_service.get_execution.called

def test_cancel_execution(mock_exec_service):
    exec_id = uuid.uuid4()
    
    mock_execution = MagicMock()
    mock_execution.id = exec_id
    mock_execution.benchmark_version_id = uuid.uuid4()
    mock_execution.status.value = "CANCELLING"
    mock_execution.attempts = []
    
    mock_exec_service.cancel_execution.return_value = mock_execution
    
    response = client.post(f"/api/v1/executions/{exec_id}/cancel")
    
    assert response.status_code == 200
    assert response.json()["id"] == str(exec_id)
    assert response.json()["status"] == "CANCELLING"
    assert mock_exec_service.cancel_execution.called

def test_cancel_execution_not_found(mock_exec_service):
    exec_id = uuid.uuid4()
    mock_exec_service.cancel_execution.side_effect = ValueError("Execution not found")
    
    response = client.post(f"/api/v1/executions/{exec_id}/cancel")
    
    assert response.status_code == 404
