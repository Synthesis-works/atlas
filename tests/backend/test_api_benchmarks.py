import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from apps.backend.main import app
from apps.backend.dependencies import (
    get_benchmark_service,
    require_authenticated
)
from apps.backend.authz import get_project_authz_service
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.core import OrganizationRole
from atlas_db.models.authoring import Benchmark, BenchmarkVersion

def test_list_benchmarks_success():
    """VIEWER should be able to list benchmarks"""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    mock_authz = Mock()
    mock_authz.authorize_project_access.return_value = True

    mock_benchmark_service = Mock()
    benchmark1 = Benchmark(
        id=uuid.uuid4(),
        project_id=project_id,
        name="Benchmark 1",
        created_at=datetime.utcnow()
    )
    mock_benchmark_service.list_benchmarks.return_value = [benchmark1]

    def override_claims():
        return TokenClaims(sub=user_id, exp=0, iat=0, jti=uuid.uuid4(), organization_id=uuid.uuid4(), membership_id=uuid.uuid4())

    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_benchmark_service] = lambda: mock_benchmark_service
    app.dependency_overrides[require_authenticated] = override_claims

    client = TestClient(app)
    response = client.get(f"/api/v1/projects/{project_id}/benchmarks")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Benchmark 1"
    
    # Verify authz was called with VIEWER allowed
    mock_authz.authorize_project_access.assert_called_once()
    kwargs = mock_authz.authorize_project_access.call_args.kwargs
    assert OrganizationRole.VIEWER in kwargs["allowed_roles"]

def test_create_benchmark_success():
    """MEMBER+ should be able to create benchmarks"""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    benchmark_id = uuid.uuid4()
    
    mock_authz = Mock()
    mock_authz.authorize_project_access.return_value = True

    mock_benchmark_service = Mock()
    benchmark = Benchmark(
        id=benchmark_id,
        project_id=project_id,
        name="New Benchmark",
        objective="Test",
        created_at=datetime.utcnow()
    )
    # The real service returns the Benchmark object
    mock_benchmark_service.create_benchmark.return_value = benchmark

    def override_claims():
        return TokenClaims(sub=user_id, exp=0, iat=0, jti=uuid.uuid4(), organization_id=uuid.uuid4(), membership_id=uuid.uuid4())

    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_benchmark_service] = lambda: mock_benchmark_service
    app.dependency_overrides[require_authenticated] = override_claims

    client = TestClient(app)
    payload = {
        "name": "New Benchmark",
        "objective": "Test",
        "initial_version": {
            "version_string": "v1.0"
        }
    }
    response = client.post(f"/api/v1/projects/{project_id}/benchmarks", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Benchmark"
    
    # Verify VIEWER is NOT allowed to create
    mock_authz.authorize_project_access.assert_called_once()
    kwargs = mock_authz.authorize_project_access.call_args.kwargs
    assert OrganizationRole.VIEWER not in kwargs["allowed_roles"]
    assert OrganizationRole.MEMBER in kwargs["allowed_roles"]

def test_create_benchmark_version():
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    benchmark_id = uuid.uuid4()
    ds_version_id = uuid.uuid4()
    
    mock_authz = Mock()
    mock_authz.authorize_project_access.return_value = True

    mock_benchmark_service = Mock()
    # Need to return a non-archived benchmark so the router allows it
    benchmark = Benchmark(id=benchmark_id, project_id=project_id, name="BM")
    mock_benchmark_service.get_benchmark.return_value = benchmark

    new_ver = BenchmarkVersion(
        id=uuid.uuid4(),
        benchmark_id=benchmark_id,
        version_string="v2.0",
        primary_dataset_version_id=ds_version_id,
        created_at=datetime.utcnow()
    )
    mock_benchmark_service.create_benchmark_version.return_value = new_ver

    def override_claims():
        return TokenClaims(sub=user_id, exp=0, iat=0, jti=uuid.uuid4(), organization_id=uuid.uuid4(), membership_id=uuid.uuid4())

    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_benchmark_service] = lambda: mock_benchmark_service
    app.dependency_overrides[require_authenticated] = override_claims

    client = TestClient(app)
    payload = {
        "version_string": "v2.0",
        "primary_dataset_version_id": str(ds_version_id),
        "evaluation_config": {"metric": "accuracy"}
    }
    response = client.post(f"/api/v1/projects/{project_id}/benchmarks/{benchmark_id}/versions", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["version_string"] == "v2.0"
    assert data["primary_dataset_version_id"] == str(ds_version_id)
