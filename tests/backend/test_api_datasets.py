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
    mock_dataset.versions = []
    mock_dataset.total_tasks = 0
    mock_dataset.sample_tasks = []

    mock_dataset_service.create_dataset.return_value = mock_dataset

    payload = {"name": "test dataset", "description": "desc"}
    response = client.post(f"/api/v1/projects/{project_id}/datasets", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == "test dataset"
    assert response.json()["status"] == "active"


from apps.backend.schemas.datasets import DatasetRead
from atlas_db.models.dataset import DatasetStatus


def _mock_read(payload: dict, project_id, member_id, dataset_id):
    return DatasetRead(
        id=dataset_id,
        project_id=project_id,
        created_by_member_id=member_id,
        status=DatasetStatus.ACTIVE,
        created_at="2026-07-16T12:00:00Z",
        updated_at="2026-07-16T12:00:00Z",
        name=payload.get("name", "dataset"),
        description=payload.get("description"),
        versions=[],
        total_tasks=0,
        sample_tasks=[],
    )


def test_update_dataset(
    client: TestClient, mock_dataset_service, mock_authz_service, mock_token_claims
):
    app.dependency_overrides[get_dataset_service] = lambda: mock_dataset_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    app.dependency_overrides[require_authenticated] = lambda: mock_token_claims

    project_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    member_id = uuid.uuid4()
    mock_authz_service.authorize_project_access.return_value = Mock(id=member_id)

    payload = {"name": "renamed", "description": "new desc"}
    mock_dataset_service.update_dataset.return_value = _mock_read(
        payload, project_id, member_id, dataset_id
    )

    response = client.put(f"/api/v1/projects/{project_id}/datasets/{dataset_id}", json=payload)

    assert response.status_code == 200
    assert response.json()["name"] == "renamed"
    assert response.json()["description"] == "new desc"


def test_update_dataset_not_found(
    client: TestClient, mock_dataset_service, mock_authz_service, mock_token_claims
):
    app.dependency_overrides[get_dataset_service] = lambda: mock_dataset_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    app.dependency_overrides[require_authenticated] = lambda: mock_token_claims

    project_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    mock_authz_service.authorize_project_access.return_value = Mock(id=uuid.uuid4())
    mock_dataset_service.update_dataset.return_value = None

    response = client.put(
        f"/api/v1/projects/{project_id}/datasets/{dataset_id}", json={"name": "x"}
    )
    assert response.status_code == 404


def test_upload_dataset_tasks(
    client: TestClient, mock_dataset_service, mock_authz_service, mock_token_claims
):
    app.dependency_overrides[get_dataset_service] = lambda: mock_dataset_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    app.dependency_overrides[require_authenticated] = lambda: mock_token_claims

    project_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    member_id = uuid.uuid4()
    mock_authz_service.authorize_project_access.return_value = Mock(id=member_id)

    from atlas_db.models.dataset import DatasetLifecycle

    mock_version = Mock()
    mock_version.id = uuid.uuid4()
    mock_version.dataset_id = dataset_id
    mock_version.version_string = "v2.0.0"
    mock_version.storage_path = f"datasets/{dataset_id}/v2.0.0"
    mock_version.checksum = None
    mock_version.schema_def = None
    mock_version.lifecycle = DatasetLifecycle.UPLOADED
    mock_version.version_number = 2
    mock_version.created_at = "2026-07-16T12:00:00Z"
    mock_version.created_by_id = member_id
    mock_dataset_service.upload_tasks.return_value = mock_version

    payload = {
        "version_string": "v2.0.0",
        "tasks": [{"input": {"text": "hi"}, "expected_output": {"answer": "hello"}}],
    }
    response = client.post(
        f"/api/v1/projects/{project_id}/datasets/{dataset_id}/tasks", json=payload
    )

    assert response.status_code == 201
    mock_dataset_service.upload_tasks.assert_called_once()


def test_validate_dataset(
    client: TestClient, mock_dataset_service, mock_authz_service, mock_token_claims
):
    app.dependency_overrides[get_dataset_service] = lambda: mock_dataset_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    app.dependency_overrides[require_authenticated] = lambda: mock_token_claims

    project_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    mock_authz_service.authorize_project_access.return_value = Mock(id=uuid.uuid4())

    from apps.backend.schemas.datasets import DatasetValidationResult
    from atlas_db.models.dataset import DatasetLifecycle

    mock_dataset_service.validate_dataset.return_value = DatasetValidationResult(
        dataset_id=dataset_id,
        version_id=uuid.uuid4(),
        lifecycle=DatasetLifecycle.VALID,
        valid=True,
        task_count=2,
        messages=["Dataset schema is valid."],
    )

    response = client.post(f"/api/v1/projects/{project_id}/datasets/{dataset_id}/validate")

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["task_count"] == 2
