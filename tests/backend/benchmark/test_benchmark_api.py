from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from atlas_db.models.core import MembershipStatus, OrganizationMember, OrganizationRole
from fastapi.testclient import TestClient

from apps.backend.dependencies import (
    get_benchmark_app_service,
    require_authenticated,
)
from apps.backend.authz import get_project_authz_service
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.benchmarks import BenchmarkRead

client = TestClient(app)

mock_app_service = MagicMock()
mock_authz_service = MagicMock()


def override_get_benchmark_app_service():
    return mock_app_service


def override_get_project_authz_service():
    return mock_authz_service


def override_require_authenticated():
    return TokenClaims(sub=uuid4(), exp=0, iat=0, jti=uuid4(), membership_id=uuid4())


@pytest.fixture(autouse=True)
def apply_dependency_overrides():
    app.dependency_overrides[get_benchmark_app_service] = override_get_benchmark_app_service
    app.dependency_overrides[get_project_authz_service] = override_get_project_authz_service
    app.dependency_overrides[require_authenticated] = override_require_authenticated
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_mocks():
    mock_app_service.reset_mock()
    mock_authz_service.reset_mock()

    mock_authz_service.authorize_project_access.return_value = OrganizationMember(
        id=uuid4(),
        user_id=uuid4(),
        organization_id=uuid4(),
        role=OrganizationRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )


def test_create_benchmark():
    project_id = uuid4()
    mock_app_service.create_benchmark.return_value = BenchmarkRead(
        id=uuid4(), project_id=project_id, state="PROPOSAL", name="Test Bench"
    )

    response = client.post(f"/api/v1/projects/{project_id}/benchmarks", json={"name": "Test Bench"})

    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Test Bench"


from apps.backend.schemas.query import PageResponse


def test_list_benchmarks():
    project_id = uuid4()
    mock_app_service.get_benchmarks_paginated.return_value = PageResponse(
        items=[
            BenchmarkRead(id=uuid4(), project_id=project_id, state="PROPOSAL", name="Test Bench")
        ],
        total=1,
        limit=50,
        offset=0,
    )

    response = client.get(f"/api/v1/projects/{project_id}/benchmarks")
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) == 1


def test_get_benchmark():
    bench_id = uuid4()
    project_id = uuid4()
    mock_app_service.get_benchmark.return_value = BenchmarkRead(
        id=bench_id, project_id=project_id, state="PROPOSAL", name="Test Bench"
    )

    response = client.get(f"/api/v1/benchmarks/{bench_id}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Test Bench"


def test_update_benchmark():
    bench_id = uuid4()
    project_id = uuid4()

    # Needs to return benchmark on get_benchmark for authorization
    mock_app_service.get_benchmark.return_value = BenchmarkRead(
        id=bench_id, project_id=project_id, state="PROPOSAL", name="Old Bench"
    )

    mock_app_service.update_benchmark.return_value = BenchmarkRead(
        id=bench_id, project_id=project_id, state="PROPOSAL", name="New Bench"
    )

    response = client.put(f"/api/v1/benchmarks/{bench_id}", json={"name": "New Bench"})

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "New Bench"


def test_delete_benchmark():
    bench_id = uuid4()
    project_id = uuid4()

    mock_app_service.get_benchmark.return_value = BenchmarkRead(
        id=bench_id, project_id=project_id, state="PROPOSAL", name="Bench"
    )

    response = client.delete(f"/api/v1/benchmarks/{bench_id}")
    assert response.status_code == 204
