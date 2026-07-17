import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from apps.backend.main import app
from apps.backend.schemas.executions import ExecutionResponse
from apps.backend.services.executions import ExecutionService
from apps.backend.dependencies import get_current_user
from apps.backend.authz import get_project_authz_service, ProjectAuthorizationService
from atlas_db.models.execution import ExecutionStatus
from datetime import datetime

# Setup basic mocks
@pytest.fixture
def mock_authz_service():
    return Mock(spec=ProjectAuthorizationService)

@pytest.fixture
def mock_execution_service():
    return Mock(spec=ExecutionService)

@pytest.fixture
def test_client(mock_authz_service):
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    # Mock current user for endpoints
    from atlas_db.models.core import User
    mock_user = User(
        id=uuid.uuid4(), email="test@example.com", is_active=True, is_verified=True, full_name="Test User"
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_create_execution(test_client):
    project_id = uuid.uuid4()
    benchmark_id = uuid.uuid4()
    exec_id = uuid.uuid4()
    
    with patch("apps.backend.routers.executions.ExecutionService.create_execution") as mock_create:
        mock_create.return_value = ExecutionResponse(
            id=exec_id,
            project_id=project_id,
            benchmark_version_id=benchmark_id,
            submitted_by_id=uuid.uuid4(),
            status=ExecutionStatus.QUEUED,
            target_model="gpt-4",
            execution_config={},
            benchmark_hash="hash",
            cancellation_requested=False,
            total_items=0,
            completed_items=0,
            started_at=None,
            completed_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        with patch("apps.backend.routers.executions.ProjectAuthorizationService.authorize_project_access") as mock_authz:
            mock_authz.return_value = Mock(id=uuid.uuid4())
            
            response = test_client.post(
                f"/api/v1/projects/{project_id}/executions",
                json={
                    "benchmark_version_id": str(benchmark_id),
                    "target_model": "gpt-4",
                    "execution_config": {}
                }
            )
            
            assert response.status_code == 201
            assert response.json()["status"] == "QUEUED"
            assert response.json()["id"] == str(exec_id)

def test_list_executions(test_client):
    project_id = uuid.uuid4()
    
    with patch("apps.backend.routers.executions.ExecutionService.list_executions_for_project") as mock_list:
        mock_list.return_value = []
        with patch("apps.backend.routers.executions.ProjectAuthorizationService.authorize_project_access") as mock_authz:
            response = test_client.get(f"/api/v1/projects/{project_id}/executions")
            assert response.status_code == 200
            assert response.json() == []

def test_cancel_execution(test_client):
    project_id = uuid.uuid4()
    exec_id = uuid.uuid4()
    
    with patch("apps.backend.routers.executions.ExecutionService.get_execution") as mock_get:
        mock_get.return_value = Mock(project_id=project_id)
        
        with patch("apps.backend.routers.executions.ExecutionService.update_status") as mock_update:
            mock_update.return_value = ExecutionResponse(
                id=exec_id,
                project_id=project_id,
                benchmark_version_id=uuid.uuid4(),
                submitted_by_id=uuid.uuid4(),
                status=ExecutionStatus.CANCELLED,
                target_model="gpt-4",
                execution_config={},
                benchmark_hash="hash",
                cancellation_requested=True,
                total_items=0,
                completed_items=0,
                started_at=None,
                completed_at=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            with patch("apps.backend.routers.executions.ProjectAuthorizationService.authorize_project_access") as mock_authz:
                response = test_client.post(f"/api/v1/projects/{project_id}/executions/{exec_id}/cancel")
                assert response.status_code == 200
                assert response.json()["status"] == "CANCELLED"
