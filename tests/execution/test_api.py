import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from apps.backend.dependencies import require_authenticated
from apps.backend.main import app
from apps.backend.routers.executions import get_execution_service
from apps.backend.schemas.auth import TokenClaims
from packages.execution_engine.application.execution_app_service import ExecutionApplicationService
from packages.execution_engine.domain.exceptions import ExecutionNotFoundError
from packages.execution_engine.domain.models import Execution, ExecutionState
from apps.backend.routers.executions import get_project_authz_service

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

@pytest.fixture
def mock_project_authz():
    service = MagicMock()
    app.dependency_overrides[get_project_authz_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_project_authz_service, None)


def test_create_execution(mock_exec_service):
    bv_id = uuid.uuid4()
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


def test_get_execution(mock_exec_service, mock_project_authz):
    exec_id = uuid.uuid4()
    project_id = uuid.uuid4()
    mock_execution = Execution(
        id=exec_id,
        project_id=project_id,
        benchmark_version_id=uuid.uuid4(),
        status=ExecutionState.RUNNING,
    )
    mock_exec_service.get_execution.return_value = mock_execution

    response = client.get(f"/api/v1/projects/{project_id}/executions/{exec_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(exec_id)
    assert mock_exec_service.get_execution.called


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
