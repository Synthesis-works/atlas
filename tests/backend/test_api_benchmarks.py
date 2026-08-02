import uuid
from datetime import datetime
from unittest.mock import Mock

from atlas_db.models.core import OrganizationRole
from fastapi.testclient import TestClient

from apps.backend.authz import get_project_authz_service
from apps.backend.dependencies import get_benchmark_app_service, require_authenticated
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.benchmarks import BenchmarkRead, BenchmarkVersionRead


def test_list_benchmarks_success():
    """VIEWER should be able to list benchmarks"""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_authz = Mock()
    mock_authz.authorize_project_access.return_value = True

    from apps.backend.schemas.query import PageResponse

    mock_benchmark_service = Mock()
    benchmark1 = BenchmarkRead(
        id=uuid.uuid4(), project_id=project_id, name="Benchmark 1", state="draft"
    )
    mock_benchmark_service.get_benchmarks_paginated.return_value = PageResponse(
        items=[benchmark1], total=1, limit=50, offset=0
    )

    def override_claims():
        return TokenClaims(
            sub=user_id,
            exp=0,
            iat=0,
            jti=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            membership_id=uuid.uuid4(),
        )

    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_benchmark_app_service] = lambda: mock_benchmark_service
    app.dependency_overrides[require_authenticated] = override_claims

    client = TestClient(app)
    response = client.get(f"/api/v1/projects/{project_id}/benchmarks")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Benchmark 1"

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
    benchmark = BenchmarkRead(
        id=benchmark_id,
        project_id=project_id,
        name="New Benchmark",
        state="draft",
    )
    mock_benchmark_service.create_benchmark.return_value = benchmark

    def override_claims():
        return TokenClaims(
            sub=user_id,
            exp=0,
            iat=0,
            jti=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            membership_id=uuid.uuid4(),
        )

    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_benchmark_app_service] = lambda: mock_benchmark_service
    app.dependency_overrides[require_authenticated] = override_claims

    client = TestClient(app)
    payload = {
        "name": "New Benchmark",
        "objective": "Test",
        "initial_version": {"version_string": "v1.0"},
    }
    response = client.post(f"/api/v1/projects/{project_id}/benchmarks", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    data = body["data"]
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
    mock_authz.authorize_project_access.return_value = Mock(role=OrganizationRole.MEMBER)

    mock_benchmark_service = Mock()
    # Need to return a non-archived benchmark so the router allows it
    benchmark = BenchmarkRead(id=benchmark_id, project_id=project_id, name="BM", state="draft")
    mock_benchmark_service.get_benchmark.return_value = benchmark

    new_ver = BenchmarkVersionRead(
        id=uuid.uuid4(),
        benchmark_id=benchmark_id,
        version_string="v2.0",
        state="DRAFT",
        dataset_version_ids=[ds_version_id],
    )
    mock_benchmark_service.create_version.return_value = new_ver

    def override_claims():
        return TokenClaims(
            sub=user_id,
            exp=0,
            iat=0,
            jti=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            membership_id=uuid.uuid4(),
        )

    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_benchmark_app_service] = lambda: mock_benchmark_service
    app.dependency_overrides[require_authenticated] = override_claims

    client = TestClient(app)
    payload = {
        "version_string": "v2.0",
        "dataset_version_ids": [str(ds_version_id)],
    }
    response = client.post(f"/api/v1/benchmarks/{benchmark_id}/versions", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    data = body["data"]
    assert data["version_string"] == "v2.0"
    assert data["dataset_version_ids"] == [str(ds_version_id)]
