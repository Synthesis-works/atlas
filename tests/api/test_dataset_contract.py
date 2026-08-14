"""
Contract & Schema Integration Tests — Dataset Management API (Milestone 4)
Validates GET /api/v1/datasets, GET /api/v1/datasets/{dataset_id}, UUID integrity, and response DTO structure.
"""

import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from apps.backend.main import app
from apps.backend.dependencies import get_db_session, get_dataset_service, require_authenticated
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.dataset import Dataset, DatasetStatus


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dataset_dependencies():
    """Supply mock dataset service for dataset contract testing."""
    sample_dataset_id = uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
    sample_project_id = uuid.UUID("11111111-2222-3333-4444-555555555555")

    dataset_domain = Dataset(
        id=sample_dataset_id,
        project_id=sample_project_id,
        name="MMLU-Pro Test Set",
        description="Massive Multitask Language Understanding Pro Dataset",
        status=DatasetStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_service = MagicMock()
    mock_service.list_all_datasets.return_value = [dataset_domain]
    mock_service.get_dataset.side_effect = lambda ds_id: dataset_domain if ds_id == sample_dataset_id else None
    mock_service.create_dataset.side_effect = lambda project_id, user_id, data: Dataset(
        id=uuid.uuid4(),
        project_id=project_id,
        name=data.name,
        description=data.description,
        status=DatasetStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )

    from apps.backend.authz import get_project_authz_service
    
    mock_authz = MagicMock()
    # Mock authorize_project_access to return a mock member instance with id
    mock_member = MagicMock()
    mock_member.id = uuid.uuid4()
    mock_authz.authorize_project_access.return_value = mock_member
    
    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_dataset_service] = lambda: mock_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz
    
    yield
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_dataset_service, None)
    app.dependency_overrides.pop(get_project_authz_service, None)



def test_get_datasets_catalog_contract():
    """Verify GET /api/v1/datasets returns a list of DatasetRead DTOs."""
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    datasets = response.json()
    assert isinstance(datasets, list), "Expected response to be a list"
    assert len(datasets) >= 1, "Expected at least 1 dataset"
    
    ds = datasets[0]
    assert "id" in ds, "Dataset missing 'id'"
    assert "name" in ds, "Dataset missing 'name'"
    assert "status" in ds, "Dataset missing 'status'"
    assert ds["name"] == "MMLU-Pro Test Set"


def test_get_dataset_by_id_contract():
    """Verify GET /api/v1/datasets/{dataset_id} returns DatasetRead DTO."""
    valid_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    response = client.get(f"/api/v1/datasets/{valid_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    ds = response.json()
    assert ds["id"] == valid_id
    assert ds["name"] == "MMLU-Pro Test Set"


def test_get_dataset_not_found_returns_404():
    """Verify GET /api/v1/datasets/{non_existent_id} returns 404 Not Found."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/datasets/{random_id}")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"


def test_get_dataset_invalid_uuid_returns_422():
    """Verify GET /api/v1/datasets/invalid-uuid returns 422 Unprocessable Entity."""
    response = client.get("/api/v1/projects/11111111-2222-3333-4444-555555555555/datasets/invalid-uuid")
    assert response.status_code == 422, f"Expected 422 for invalid UUID, got {response.status_code}"


def test_post_global_dataset_creation_contract():
    """Verify POST /api/v1/datasets creates new dataset."""
    payload = {
        "name": "Custom Math Benchmark Dataset",
        "description": "GSM8K evaluation math prompts",
        "is_public": True,
    }
    response = client.post("/api/v1/projects/11111111-2222-3333-4444-555555555555/datasets", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    ds = response.json()
    assert ds["name"] == "Custom Math Benchmark Dataset"
    assert "id" in ds

