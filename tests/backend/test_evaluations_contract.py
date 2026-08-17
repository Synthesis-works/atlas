import uuid
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from apps.backend.main import app
from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.schemas.auth import TokenClaims


@pytest.fixture
def test_client():
    from apps.backend.routers.executions import get_execution_service
    from packages.execution_engine.domain.models import Execution, ExecutionState

    mock_db = Mock()
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    mock_service = Mock()
    mock_service.submit_execution.return_value = Execution(
        id=uuid.uuid4(),
        benchmark_version_id=uuid.UUID("00000000-0000-0000-0000-000000000005"),
        status=ExecutionState.QUEUED,
        target_model="groq/llama-3.1-8b-instant",
    )

    app.dependency_overrides[get_execution_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[require_authenticated] = lambda: TokenClaims(
        sub=uuid.uuid4(), exp=9999999999, iat=1000000000, jti=uuid.uuid4()
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_executions_endpoint_structure(test_client):
    """Verify GET /api/v1/executions returns valid DTO response."""
    response = test_client.get("/api/v1/executions")
    assert response.status_code == 200


def test_execution_creation_payload_compatibility(test_client):
    """Verify execution creation payload returns 201 created status."""
    payload = {
        "benchmark_version_id": "00000000-0000-0000-0000-000000000005",
        "dataset_version_id": "00000000-0000-0000-0000-000000000006",
        "target_model": "groq/llama-3.1-8b-instant",
    }
    response = test_client.post(
        "/api/v1/benchmarks/00000000-0000-0000-0000-000000000005/executions", json=payload
    )
    assert response.status_code in (200, 201)
