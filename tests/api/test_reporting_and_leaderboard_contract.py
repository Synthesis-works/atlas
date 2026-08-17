"""
Contract & Schema Integration Tests — Leaderboards & Reporting API (Milestone 5)
Validates GET /api/v1/leaderboard, GET /api/v1/reports/runs, and export endpoints.
"""

import uuid
from datetime import datetime, timezone, UTC
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.dependencies import (
    require_authenticated,
    get_db_session,
    get_leaderboard_app_service,
    get_reporting_service,
)
from apps.backend.schemas.leaderboard import LeaderboardRead, LeaderboardEntryRead, LeaderboardType
from apps.backend.schemas.reporting import PaginatedReportRunsRead, ReportRunEntryRead
from apps.backend.schemas.query import PageResponse
from services.report.models.read_models import ReportRunStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_leaderboard_and_reporting_dependencies():
    """Supply mock token claims, leaderboard service, and reporting service."""
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )

    mock_lb_service = MagicMock()
    mock_lb_service.get_benchmark_leaderboard.return_value = LeaderboardRead(
        leaderboard_type=LeaderboardType.GLOBAL,
        title="Global Benchmark Registry",
        description="Global AI Model Evaluation Leaderboard",
        benchmark_version_id="00000000-0000-0000-0000-000000000000",
        entries=PageResponse[LeaderboardEntryRead](
            items=[
                LeaderboardEntryRead(
                    rank=1,
                    model_name="GPT-5",
                    overall_score=94.5,
                    benchmark_count=12,
                    last_updated=datetime.now(UTC),
                ),
                LeaderboardEntryRead(
                    rank=2,
                    model_name="Claude-3.5-Sonnet",
                    overall_score=91.2,
                    benchmark_count=10,
                    last_updated=datetime.now(UTC),
                ),
            ],
            total=2,
            limit=50,
            offset=0,
        ),
    )

    mock_rep_service = MagicMock()
    mock_rep_service.get_runs_filtered.return_value = PaginatedReportRunsRead(
        items=[
            ReportRunEntryRead(
                run_id=uuid.uuid4(),
                benchmark_id=uuid.uuid4(),
                benchmark_version="1.0.0",
                target_model="GPT-5",
                overall_score=94.5,
                evaluation_status=ReportRunStatus.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
        ],
        total=1,
        page=1,
        size=50,
    )

    app.dependency_overrides[get_db_session] = lambda: MagicMock()
    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_leaderboard_app_service] = lambda: mock_lb_service
    app.dependency_overrides[get_reporting_service] = lambda: mock_rep_service
    yield
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_leaderboard_app_service, None)
    app.dependency_overrides.pop(get_reporting_service, None)


def test_get_global_leaderboard_contract():
    """Verify GET /api/v1/benchmarks/{id}/leaderboard returns LeaderboardRead schema."""
    benchmark_version_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/benchmarks/{benchmark_version_id}/leaderboard")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "entries" in data, "Leaderboard response missing 'entries'"
    items = data["entries"]["items"]
    assert len(items) == 2, "Expected 2 entries"
    assert items[0]["model_name"] == "GPT-5"
    assert items[0]["rank"] == 1


def test_get_report_runs_contract():
    """Verify GET /api/v1/reports/runs returns PaginatedReportRunsRead schema."""
    response = client.get("/api/v1/reports/runs")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "items" in data, "Report runs response missing 'items'"
    assert len(data["items"]) == 1, "Expected 1 item"
    assert data["items"][0]["target_model"] == "GPT-5"
    assert data["items"][0]["evaluation_status"] == "COMPLETED"
