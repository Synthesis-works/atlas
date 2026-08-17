import uuid
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import get_current_user
from apps.backend.main import app


@pytest.fixture
def test_client():
    mock_authz_service = Mock(spec=ProjectAuthorizationService)
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service

    from atlas_db.models.core import User

    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        is_active=True,
        is_verified=True,
        full_name="Test User",
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_evaluate_execution_authorized(test_client):
    project_id = uuid.uuid4()
    execution_id = uuid.uuid4()

    # We patch ProjectAuthorizationService directly because it's instantiated inside the router
    with patch("apps.backend.routers.evaluation.ProjectAuthorizationService") as mock_authz_cls:
        mock_authz = mock_authz_cls.return_value
        mock_authz.authorize_project_access.return_value = True

        with patch("apps.backend.routers.evaluation.EvaluationService") as mock_eval_service_cls:
            mock_eval_service = mock_eval_service_cls.return_value

            # Setup execution check
            mock_execution = Mock()
            mock_execution.project_id = project_id
            mock_eval_service.execution_repo.get.return_value = mock_execution

            with patch("apps.backend.worker.evaluation_tasks.run_evaluation_task") as mock_task:
                response = test_client.post(
                    f"/api/v1/projects/{project_id}/executions/{execution_id}/evaluate"
                )

                assert response.status_code == 202
                data = response.json()
                assert data["execution_id"] == str(execution_id)
                assert data["status"] == "QUEUED"

                mock_task.delay.assert_called_once_with(str(execution_id))


def test_evaluate_execution_forbidden(test_client):
    project_id = uuid.uuid4()
    execution_id = uuid.uuid4()

    with patch("apps.backend.routers.evaluation.ProjectAuthorizationService") as mock_authz_cls:
        mock_authz = mock_authz_cls.return_value
        mock_authz.authorize_project_access.return_value = False

        response = test_client.post(
            f"/api/v1/projects/{project_id}/executions/{execution_id}/evaluate"
        )

        assert response.status_code == 403
