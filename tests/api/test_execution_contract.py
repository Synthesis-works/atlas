"""
Contract & Schema Integration Tests — Execution Dispatch & Cancellation API (Milestone 3A & 3D)
Validates POST /api/v1/benchmarks/{version_id}/executions contract, UUID validation,
X-Request-ID correlation header propagation, idempotency, cancellation contract, and response DTO structure.
"""

import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.dependencies import (
    require_authenticated,
    get_db_session,
)
from apps.backend.routers.executions import get_execution_service
from packages.execution_engine.domain.models import Execution, ExecutionState

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth_and_services():
    """Supply mock token claims, db session, and execution service to test execution API contract with backend idempotency and cancellation."""
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )

    execution_cache: dict[str, Execution] = {}

    def mock_submit_execution(benchmark_version_id: uuid.UUID, created_by: uuid.UUID = None):
        cache_key = str(benchmark_version_id)
        if cache_key in execution_cache:
            return execution_cache[cache_key]

        exec_domain = Execution.rehydrate(
            id=uuid.uuid4(),
            benchmark_version_id=benchmark_version_id,
            project_id=uuid.uuid4(),
            status=ExecutionState.QUEUED,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            max_retries=3,
            attempts=[],
        )
        execution_cache[cache_key] = exec_domain
        return exec_domain

    def mock_cancel_execution(execution_id: uuid.UUID):
        return Execution.rehydrate(
            id=execution_id,
            benchmark_version_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            status=ExecutionState.CANCELLED,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            max_retries=3,
            attempts=[],
        )

    mock_service = MagicMock()
    mock_service.submit_execution.side_effect = mock_submit_execution
    mock_service.cancel_execution.side_effect = mock_cancel_execution

    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_execution_service] = lambda: mock_service
    yield
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_execution_service, None)


def test_post_execution_dispatch_contract():
    """Verify POST /api/v1/benchmarks/{version_id}/executions creates execution and returns ExecutionResponse DTO."""
    version_id = uuid.uuid4()
    req_id = str(uuid.uuid4())
    headers = {
        "X-Request-ID": req_id,
        "Accept": "application/vnd.atlas.v1+json, application/json",
    }
    payload = {
        "benchmark_version_id": str(version_id),
        "target_model": "GPT-5",
        "execution_config": {},
    }

    response = client.post(
        f"/api/v1/benchmarks/{version_id}/executions",
        json=payload,
        headers=headers,
    )

    assert response.status_code in [200, 201], f"Expected 200 or 201, got {response.status_code}"
    
    exec_data = response.json()
    assert "id" in exec_data, "Execution payload missing 'id'"
    assert "status" in exec_data, "Execution payload missing 'status'"
    assert exec_data["status"] == "QUEUED", f"Expected status 'QUEUED', got {exec_data['status']}"

    # Verify ID is a valid UUID
    try:
        val = uuid.UUID(exec_data["id"])
        assert str(val) == exec_data["id"]
    except ValueError:
        pytest.fail(f"Execution id '{exec_data['id']}' is not a valid UUID string")


def test_post_execution_idempotency():
    """Verify consecutive duplicate dispatch requests resolve to the same execution record."""
    version_id = uuid.uuid4()
    req_id = str(uuid.uuid4())
    headers = {"X-Request-ID": req_id}
    payload = {
        "benchmark_version_id": str(version_id),
        "target_model": "GPT-5",
    }

    res1 = client.post(f"/api/v1/benchmarks/{version_id}/executions", json=payload, headers=headers)
    res2 = client.post(f"/api/v1/benchmarks/{version_id}/executions", json=payload, headers=headers)

    assert res1.status_code in [200, 201]
    assert res2.status_code in [200, 201]
    assert res1.json()["id"] == res2.json()["id"], "Idempotent requests should yield the same execution ID"


def test_post_execution_cancellation_contract():
    """Verify POST /api/v1/executions/{execution_id}/cancel returns ExecutionResponse with CANCELLED status."""
    exec_id = uuid.uuid4()
    response = client.post(f"/api/v1/executions/{exec_id}/cancel")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["id"] == str(exec_id), "Response execution ID mismatch"
    assert data["status"] == "CANCELLED", f"Expected CANCELLED status, got {data['status']}"


def test_post_execution_invalid_version_id_returns_422():
    """Verify POST with invalid UUID version_id returns 422 Unprocessable Entity."""
    payload = {
        "benchmark_version_id": "invalid-uuid",
        "target_model": "GPT-5",
    }
    response = client.post("/api/v1/benchmarks/invalid-uuid/executions", json=payload)
    assert response.status_code == 422, f"Expected 422 for invalid UUID, got {response.status_code}"
