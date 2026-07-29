from uuid import uuid4

from fastapi.testclient import TestClient

from apps.backend.main import app
from apps.backend.dependencies import get_benchmark_app_service, require_authenticated
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.query import PageResponse
from apps.backend.schemas.benchmarks import BenchmarkRead
from unittest.mock import MagicMock

client = TestClient(app)


def test_global_benchmarks_discovery_integration():
    """
    Test that the discovery endpoint correctly accepts query layer parameters
    for filtering, sorting, and pagination.
    """
    mock_app_service = MagicMock()

    mock_app_service.get_benchmarks_paginated.return_value = PageResponse(
        items=[
            BenchmarkRead(id=uuid4(), project_id=uuid4(), state="published", name="Benchmark A"),
            BenchmarkRead(id=uuid4(), project_id=uuid4(), state="published", name="Benchmark B"),
        ],
        total=2,
        limit=10,
        offset=0,
    )

    def override_require_authenticated():
        return TokenClaims(sub=uuid4(), exp=0, iat=0, jti=uuid4(), membership_id=uuid4())

    app.dependency_overrides[get_benchmark_app_service] = lambda: mock_app_service
    app.dependency_overrides[require_authenticated] = override_require_authenticated

    cat_id = uuid4()
    cap_id = uuid4()

    response = client.get(
        "/api/v1/benchmarks",
        params={
            "limit": 10,
            "offset": 0,
            "sort": "updated_at",
            "order": "desc",
            "status": "published",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Verify that the service was called with the right mapped parameters
    mock_app_service.get_benchmarks_paginated.assert_called_once()

    call_kwargs = mock_app_service.get_benchmarks_paginated.call_args.kwargs

    page_req = call_kwargs["page_req"]
    sort_req = call_kwargs["sort_req"]
    filter_req = call_kwargs["filter_req"]
    project_id = call_kwargs["project_id"]

    assert page_req.limit == 10
    assert page_req.offset == 0
    assert sort_req.sort.value == "updated_at"
    assert sort_req.order == "desc"

    assert filter_req.status.value == "published"
    assert project_id is None
