"""
Contract & Schema Integration Tests — Benchmark Catalog API (Milestone 2.5)
Validates that backend /api/v1/benchmarks response payload structures
strictly adhere to BenchmarkMapper and frontend integration contracts.
"""

import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.benchmarks import BenchmarkRead
from apps.backend.schemas.query import PageResponse
from apps.backend.dependencies import require_authenticated, get_benchmark_app_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth_and_services():
    """Supply mock token claims and benchmark service to test API contract."""
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )

    bm_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    mock_benchmark_read = BenchmarkRead(
        id=bm_id,
        project_id=proj_id,
        state="active",
        name="MMLU-Pro",
    )

    page_res = PageResponse[BenchmarkRead](
        items=[mock_benchmark_read],
        total=1,
        limit=50,
        offset=0,
        next_cursor=None,
    )

    mock_service = MagicMock()
    mock_service.get_benchmarks_paginated.return_value = page_res
    mock_service.get_benchmark.return_value = mock_benchmark_read

    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_benchmark_app_service] = lambda: mock_service
    yield
    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_benchmark_app_service, None)


def test_get_benchmarks_catalog_contract():
    """Verify GET /api/v1/benchmarks response structure matches frontend contract."""
    response = client.get("/api/v1/benchmarks")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"

    payload = response.json()
    assert "success" in payload, "Response payload missing 'success' key"
    assert payload["success"] is True, "Expected success: true"
    assert "data" in payload, "Response payload missing 'data' key"
    
    data_env = payload["data"]
    assert "items" in data_env, "PageResponse missing 'items' key"
    benchmarks = data_env["items"]
    assert isinstance(benchmarks, list), "Expected 'items' to be an array of benchmarks"
    assert len(benchmarks) > 0, "Expected at least 1 benchmark item in catalog"

    # Validate schema for every benchmark item returned
    for item in benchmarks:
        assert "id" in item, "Benchmark item missing 'id'"
        assert "name" in item, "Benchmark item missing 'name'"
        assert "project_id" in item, "Benchmark item missing 'project_id'"
        assert "state" in item, "Benchmark item missing 'state'"
        
        # Verify ID is a valid UUID
        try:
            val = uuid.UUID(item["id"])
            assert str(val) == item["id"]
        except ValueError:
            pytest.fail(f"Benchmark id '{item['id']}' is not a valid UUID string")


def test_get_benchmark_detail_invalid_uuid_returns_422_or_404():
    """Verify GET /api/v1/benchmarks/{id} rejects non-UUID strings."""
    response = client.get("/api/v1/benchmarks/invalid-slug-string")
    assert response.status_code in [404, 422], f"Expected 404 or 422 for non-UUID string, got {response.status_code}"
