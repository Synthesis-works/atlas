"""
Contract & Schema Integration Tests — Execution Status API (Milestone 3B)
Validates GET /api/v1/executions/{id} status polling contract, response DTO structure,
and 404 behavior for unknown execution UUIDs.
"""

import uuid
from datetime import datetime, timezone, UTC
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
    """Supply mock token claims, db session, and execution service for status polling tests."""
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )

    known_exec_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    mock_exec = Execution.rehydrate(
        id=known_exec_id,
        benchmark_version_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status=ExecutionState.RUNNING,
        created_by=user_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        max_retries=3,
        attempts=[],
    )

    def mock_get_execution(execution_id: uuid.UUID):
        if execution_id == known_exec_id:
            return mock_exec
        return None

    mock_service = MagicMock()
    mock_service.get_execution.side_effect = mock_get_execution

    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_execution_service] = lambda: mock_service
    yield
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_execution_service, None)


def test_get_execution_status_contract():
    """Verify GET /api/v1/executions/{id} returns ExecutionResponse DTO for valid execution."""
    exec_id = "11111111-2222-3333-4444-555555555555"
    headers = {
        "X-Request-ID": str(uuid.uuid4()),
        "Accept": "application/vnd.atlas.v1+json, application/json",
    }

    response = client.get(f"/api/v1/executions/{exec_id}", headers=headers)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    data = response.json()
    assert data["id"] == exec_id, f"Expected ID {exec_id}, got {data['id']}"
    assert data["status"] == "RUNNING", f"Expected status RUNNING, got {data['status']}"


def test_get_execution_status_not_found():
    """Verify GET /api/v1/executions/{id} returns 404 for unknown execution ID."""
    unknown_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/executions/{unknown_id}")
    assert response.status_code == 404, f"Expected 404 for unknown execution, got {response.status_code}"
