import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from apps.backend.dependencies import get_leaderboard_app_service
from apps.backend.main import app
from apps.backend.schemas.leaderboard import LeaderboardType, LeaderboardRead
from apps.backend.schemas.query import PageResponse
from apps.backend.services.leaderboard import LeaderboardApplicationService
from atlas_db.models.authoring import BenchmarkVersion, Capability


from apps.backend.dependencies import get_leaderboard_app_service, require_authenticated
from apps.backend.schemas.auth import TokenClaims

@pytest.fixture
def mock_leaderboard_service():
    return MagicMock(spec=LeaderboardApplicationService)


@pytest.fixture
def client(mock_leaderboard_service):
    app.dependency_overrides[get_leaderboard_app_service] = lambda: mock_leaderboard_service
    app.dependency_overrides[require_authenticated] = lambda: TokenClaims(
        sub=uuid.uuid4(), exp=9999999999, iat=1000000000, jti=uuid.uuid4()
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_benchmark_leaderboard(client, mock_leaderboard_service):
    # Arrange
    benchmark_version_id = uuid.uuid4()
    
    mock_leaderboard_service.get_benchmark_leaderboard.return_value = LeaderboardRead(
        leaderboard_type=LeaderboardType.BENCHMARK,
        title="Benchmark Version 1.0.0",
        description="Leaderboard for Benchmark Version 1.0.0",
        benchmark_version_id=str(benchmark_version_id),
        entries=PageResponse(
            items=[],
            total=0,
            limit=50,
            offset=0
        )
    )

    # Act
    response = client.get(f"/api/v1/benchmarks/{benchmark_version_id}/leaderboard")

    # Assert
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "max-age=60"
    data = response.json()
    assert data["leaderboard_type"] == "BENCHMARK"
    assert data["benchmark_version_id"] == str(benchmark_version_id)
    assert data["entries"]["total"] == 0
    mock_leaderboard_service.get_benchmark_leaderboard.assert_called_once_with(
        benchmark_version_id=benchmark_version_id,
        limit=50,
        offset=0
    )


def test_get_capability_leaderboard(client, mock_leaderboard_service):
    # Arrange
    capability_id = uuid.uuid4()
    
    mock_leaderboard_service.get_capability_leaderboard.return_value = LeaderboardRead(
        leaderboard_type=LeaderboardType.CAPABILITY,
        title="Reasoning",
        description="Reasoning tasks",
        capability_id=str(capability_id),
        entries=PageResponse(
            items=[],
            total=0,
            limit=50,
            offset=0
        )
    )

    # Act
    response = client.get(f"/api/v1/capabilities/{capability_id}/leaderboard?limit=10&offset=10")

    # Assert
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "max-age=60"
    data = response.json()
    assert data["leaderboard_type"] == "CAPABILITY"
    assert data["capability_id"] == str(capability_id)
    mock_leaderboard_service.get_capability_leaderboard.assert_called_once_with(
        capability_id=capability_id,
        limit=10,
        offset=10
    )
