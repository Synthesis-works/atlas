import pytest
from fastapi.testclient import TestClient
import uuid
from typing import Any
from datetime import timedelta
from unittest.mock import MagicMock

from apps.backend.main import app
from apps.backend.worker_auth import require_worker_auth
from packages.execution_engine.application.worker_app_service import WorkerApplicationService
from apps.backend.routers.internal_workers import get_worker_service
from packages.execution_engine.domain.exceptions import ExecutionNotFoundError, LeaseOwnershipError

client = TestClient(app)

# Stub out the worker auth dependency
app.dependency_overrides[require_worker_auth] = lambda: {"worker_authenticated": True}

@pytest.fixture
def mock_worker_service():
    service = MagicMock(spec=WorkerApplicationService)
    app.dependency_overrides[get_worker_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_worker_service, None)

def test_acquire_empty_queue(mock_worker_service):
    """Worker acquires when queue empty"""
    mock_worker_service.acquire_work.return_value = None
    
    response = client.post("/api/v1/internal/workers/acquire", json={"worker_id": str(uuid.uuid4()), "capabilities": []})
    assert response.status_code == 204

def test_acquire_exactly_one(mock_worker_service):
    """Worker acquires exactly one execution"""
    worker_id = uuid.uuid4()
    mock_response = MagicMock()
    mock_response.lease_id = uuid.uuid4()
    mock_response.execution_id = uuid.uuid4()
    mock_response.attempt_id = uuid.uuid4()
    mock_response.heartbeat_interval_seconds = 60
    mock_response.lease_duration_seconds = 300
    mock_response.benchmark_version_id = uuid.uuid4()
    
    # Must convert properties to dict for fastAPI response validation
    mock_worker_service.acquire_work.return_value = mock_response
    
    # To bypass Pydantic model validation on the mock, we can just return a dict from the mock or use a real DTO
    from packages.execution_engine.api.worker_dtos import AcquireResponse
    mock_worker_service.acquire_work.return_value = AcquireResponse(
        lease_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        heartbeat_interval_seconds=60,
        lease_duration_seconds=300,
        benchmark_version_id=uuid.uuid4()
    )

    response = client.post("/api/v1/internal/workers/acquire", json={"worker_id": str(worker_id), "capabilities": []})
    assert response.status_code == 200
    assert "lease_id" in response.json()

def test_lease_renewal(mock_worker_service):
    """Lease renewal before expiry"""
    exec_id = uuid.uuid4()
    worker_id = uuid.uuid4()
    mock_worker_service.heartbeat.return_value = "2024-01-01T00:05:00Z"
    
    response = client.post(f"/api/v1/internal/workers/executions/{exec_id}/heartbeat", json={"worker_id": str(worker_id)})
    assert response.status_code == 200
    assert response.json()["lease_expires_at"] == "2024-01-01T00:05:00Z"

def test_heartbeat_after_completion(mock_worker_service):
    """Heartbeat after completion (lease lost)"""
    exec_id = uuid.uuid4()
    worker_id = uuid.uuid4()
    mock_worker_service.heartbeat.side_effect = LeaseOwnershipError("No active lease exists")
    
    response = client.post(f"/api/v1/internal/workers/executions/{exec_id}/heartbeat", json={"worker_id": str(worker_id)})
    assert response.status_code == 403

def test_completion_after_expiry(mock_worker_service):
    """Completion after lease expiry"""
    exec_id = uuid.uuid4()
    worker_id = uuid.uuid4()
    mock_worker_service.complete_success.side_effect = LeaseOwnershipError("Lease has expired")
    
    response = client.post(f"/api/v1/internal/workers/executions/{exec_id}/complete_success", json={
        "worker_id": str(worker_id),
        "artifacts": []
    })
    assert response.status_code == 403

def test_wrong_worker_heartbeat(mock_worker_service):
    """Heartbeat by wrong worker"""
    exec_id = uuid.uuid4()
    worker_id = uuid.uuid4()
    mock_worker_service.heartbeat.side_effect = LeaseOwnershipError("Worker does not own the active lease")
    
    response = client.post(f"/api/v1/internal/workers/executions/{exec_id}/heartbeat", json={"worker_id": str(worker_id)})
    assert response.status_code == 403

def test_artifact_persistence(mock_worker_service):
    """Artifact persistence on complete_success"""
    exec_id = uuid.uuid4()
    worker_id = uuid.uuid4()
    
    response = client.post(f"/api/v1/internal/workers/executions/{exec_id}/complete_success", json={
        "worker_id": str(worker_id),
        "artifacts": [{"type": "LOGS", "storage_uri": "s3://logs"}]
    })
    assert response.status_code == 200
    mock_worker_service.complete_success.assert_called_once()
    args, kwargs = mock_worker_service.complete_success.call_args
    assert kwargs['artifacts'][0].storage_uri == "s3://logs"
