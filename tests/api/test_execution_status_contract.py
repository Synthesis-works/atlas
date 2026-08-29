"""
Contract & Schema Integration Tests — Execution Status API (Milestone 3B)
Validates GET /api/v1/executions/{id} status polling contract, response DTO structure,
and 404 behavior for unknown execution UUIDs.

The read surface is the authoritative ``executions`` row (Slice 1): the endpoint
must never depend on the engine aggregate for status/timestamps/progress.
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
from atlas_db.models.execution import Execution as DBExecution, ExecutionStatus

client = TestClient(app)

_KNOWN_EXEC_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def override_auth_and_services():
    """Supply mock token claims and a shared db session carrying the authoritative row."""
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )

    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
    known_exec = DBExecution(
        id=uuid.UUID(_KNOWN_EXEC_ID),
        project_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        submitted_by_id=user_id,
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

    def first_row():
        calls = db.query.return_value.filter.call_args_list
        if calls:
            criterion = calls[-1].args[0]
            bound = getattr(getattr(criterion, "right", None), "value", None)
            return known_exec if bound == known_exec.id else None
        return None

    db.query.return_value.filter.return_value.first.side_effect = first_row

    app.dependency_overrides[get_db_session] = lambda: db
    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    yield
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(require_authenticated, None)


def test_get_execution_status_contract():
    """Verify GET /api/v1/executions/{id} returns ExecutionResponse DTO from the
    authoritative row for a valid execution."""
    headers = {
        "X-Request-ID": str(uuid.uuid4()),
        "Accept": "application/vnd.atlas.v1+json, application/json",
    }

    response = client.get(f"/api/v1/executions/{_KNOWN_EXEC_ID}", headers=headers)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"

    data = response.json()
    assert data["id"] == _KNOWN_EXEC_ID, f"Expected ID {_KNOWN_EXEC_ID}, got {data['id']}"
    assert data["status"] == "RUNNING", f"Expected status RUNNING, got {data['status']}"
    assert data["completed_items"] == 3
    assert data["total_items"] == 10
    assert data["started_at"] is not None
    assert data["completed_at"] is None


def test_get_execution_status_not_found():
    """Verify GET /api/v1/executions/{id} returns 404 for unknown execution ID."""
    unknown_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/executions/{unknown_id}")
    assert response.status_code == 404, (
        f"Expected 404 for unknown execution, got {response.status_code}"
    )
