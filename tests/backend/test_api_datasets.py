import uuid
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import get_dataset_service, require_authenticated
from apps.backend.main import app
from apps.backend.services.datasets import DatasetService


@pytest.fixture
def mock_dataset_service():
    return Mock(spec=DatasetService)


@pytest.fixture
def mock_authz_service():
    service = Mock(spec=ProjectAuthorizationService)
    return service


from apps.backend.schemas.auth import TokenClaims


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_token_claims():
    return TokenClaims(
        sub=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        exp=9999999999,
        iat=1600000000,
        jti=uuid.uuid4(),
    )


def test_list_datasets(
    client: TestClient, mock_dataset_service, mock_authz_service, mock_token_claims
):
    app.dependency_overrides[get_dataset_service] = lambda: mock_dataset_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    app.dependency_overrides[require_authenticated] = lambda: mock_token_claims

    project_id = uuid.uuid4()

    mock_authz_service.authorize_project_access.return_value = Mock(id=uuid.uuid4())
    mock_dataset_service.list_datasets.return_value = []

    response = client.get(f"/api/v1/projects/{project_id}/datasets")
    assert response.status_code == 200
    assert response.json() == []


def test_create_dataset(
    client: TestClient, mock_dataset_service, mock_authz_service, mock_token_claims
):
    app.dependency_overrides[get_dataset_service] = lambda: mock_dataset_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    app.dependency_overrides[require_authenticated] = lambda: mock_token_claims

    project_id = uuid.uuid4()

    mock_member = Mock(id=uuid.uuid4())
    mock_authz_service.authorize_project_access.return_value = mock_member

    mock_dataset = Mock()
    mock_dataset.id = uuid.uuid4()
    mock_dataset.project_id = project_id
    mock_dataset.created_by_member_id = mock_member.id
    mock_dataset.name = "test dataset"
    mock_dataset.description = "desc"
    mock_dataset.status = "active"
    mock_dataset.created_at = "2026-07-16T12:00:00Z"
    mock_dataset.updated_at = "2026-07-16T12:00:00Z"
    mock_dataset.registry_id = None
    mock_dataset.source_id = None
    mock_dataset.license_id = None

    mock_dataset_service.create_dataset.return_value = mock_dataset

    payload = {"name": "test dataset", "description": "desc"}
    response = client.post(f"/api/v1/projects/{project_id}/datasets", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == "test dataset"
    assert response.json()["status"] == "active"
