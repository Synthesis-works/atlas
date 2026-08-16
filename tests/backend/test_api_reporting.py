import uuid
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from apps.backend.dependencies import get_reporting_service, require_authenticated
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.reporting import (
    CapabilityDashboardRead,
    CapabilityScoreRead,
    PaginatedReportRunsRead,
    ReportRunEntryRead,
    ReportSummaryRead,
)
from services.report.models.read_models import ReportRunsFilter, ReportRunStatus
from services.report.services.reporting import ReportingService


@pytest.fixture
def mock_reporting_service():
    return Mock(spec=ReportingService)


@pytest.fixture
def test_client(mock_reporting_service):
    app.dependency_overrides[get_reporting_service] = lambda: mock_reporting_service
    app.dependency_overrides[require_authenticated] = lambda: TokenClaims(
        sub=uuid.uuid4(), exp=9999999999, iat=1000000000, jti=uuid.uuid4()
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_run_summary_success(test_client, mock_reporting_service):
    run_id = uuid.uuid4()
    benchmark_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_summary = ReportSummaryRead(
        run_id=run_id,
        benchmark_id=benchmark_id,
        benchmark_name="HumanEval",
        benchmark_version="1.0.0",
        target_model="gpt-4o",
        evaluation_status=ReportRunStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        overall_score=88.5,
        scores=[
            CapabilityScoreRead(capability_name="reasoning", score=92.0),
            CapabilityScoreRead(capability_name="coding", score=85.0),
        ],
    )
    mock_reporting_service.get_run_summary.return_value = mock_summary

    response = test_client.get(f"/api/v1/reports/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == str(run_id)
    assert data["benchmark_id"] == str(benchmark_id)
    assert data["benchmark_name"] == "HumanEval"
    assert data["benchmark_version"] == "1.0.0"
    assert data["target_model"] == "gpt-4o"
    assert data["evaluation_status"] == "COMPLETED"
    assert data["overall_score"] == 88.5
    assert len(data["scores"]) == 2
    assert data["scores"][0]["capability_name"] == "reasoning"
    assert data["scores"][0]["score"] == 92.0
    mock_reporting_service.get_run_summary.assert_called_once_with(run_id)


def test_get_run_summary_not_found(test_client, mock_reporting_service):
    run_id = uuid.uuid4()
    mock_reporting_service.get_run_summary.return_value = None

    response = test_client.get(f"/api/v1/reports/runs/{run_id}")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["error"]["message"].lower()
    mock_reporting_service.get_run_summary.assert_called_once_with(run_id)


def test_get_runs_filtered_empty(test_client, mock_reporting_service):
    empty_runs = PaginatedReportRunsRead(items=[], total=0, page=1, size=50)
    mock_reporting_service.get_runs_filtered.return_value = empty_runs

    response = test_client.get("/api/v1/reports/runs?limit=50&offset=100")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0
    assert data["page"] == 1


def test_export_run_results_json(test_client, mock_reporting_service):
    run_id = uuid.uuid4()
    from services.report.exporters import ExportResult

    mock_reporting_service.build_report_export.return_value = None
    mock_reporting_service.export_run_results.return_value = ExportResult(
        content=b'{"report": {"title": "Sample"}}', mime_type="application/json", filename_extension="json"
    )

    response = test_client.get(f"/api/v1/reports/runs/{run_id}/export?format=json")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert "attachment; filename=" in response.headers["Content-Disposition"]
    assert "json" in response.headers["Content-Disposition"]
    assert response.content == b'{"report": {"title": "Sample"}}'
    mock_reporting_service.export_run_results.assert_called_once()
    export_call = mock_reporting_service.export_run_results.call_args
    assert export_call.args[0] == run_id
    assert export_call.kwargs == {
        "format_type": "json",
        "include_prompt": False,
        "include_expected_output": False,
        "execution_meta": {},
        "document": None,
    }


def test_export_run_results_csv(test_client, mock_reporting_service):
    run_id = uuid.uuid4()
    from services.report.exporters import ExportResult

    mock_reporting_service.build_report_export.return_value = None
    mock_reporting_service.export_run_results.return_value = ExportResult(
        content=b"test\n1", mime_type="text/csv", filename_extension="csv"
    )

    response = test_client.get(
        f"/api/v1/reports/runs/{run_id}/export?format=csv&include_prompt=true"
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["Content-Type"]
    assert "csv" in response.headers["Content-Disposition"]
    assert response.content == b"test\n1"
    mock_reporting_service.export_run_results.assert_called_once()
    export_call = mock_reporting_service.export_run_results.call_args
    assert export_call.args[0] == run_id
    assert export_call.kwargs == {
        "format_type": "csv",
        "include_prompt": True,
        "include_expected_output": False,
        "execution_meta": {},
        "document": None,
    }


def test_export_run_results_invalid_format(test_client, mock_reporting_service):
    run_id = uuid.uuid4()
    # Pydantic validation should block invalid formats because of the regex pattern
    response = test_client.get(f"/api/v1/reports/runs/{run_id}/export?format=pdf")
    assert response.status_code == 422


def test_get_model_capabilities_success(test_client, mock_reporting_service):
    mock_dashboard = CapabilityDashboardRead(
        model_identifier="gpt-4o",
        overall_score=88.5,
        scores=[
            CapabilityScoreRead(capability_name="reasoning", score=92.0),
            CapabilityScoreRead(capability_name="coding", score=85.0),
        ],
    )
    mock_reporting_service.get_capability_dashboard.return_value = mock_dashboard

    response = test_client.get("/api/v1/reports/models/gpt-4o/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["model_identifier"] == "gpt-4o"
    assert data["overall_score"] == 88.5
    assert len(data["scores"]) == 2
    mock_reporting_service.get_capability_dashboard.assert_called_once_with("gpt-4o")


def test_get_model_capabilities_not_found(test_client, mock_reporting_service):
    mock_reporting_service.get_capability_dashboard.return_value = None

    response = test_client.get("/api/v1/reports/models/unknown-model/capabilities")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["error"]["message"].lower()
    mock_reporting_service.get_capability_dashboard.assert_called_once_with("unknown-model")


def test_list_report_runs_success_and_filtering(test_client, mock_reporting_service):
    run_id = uuid.uuid4()
    benchmark_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_entry = ReportRunEntryRead(
        run_id=run_id,
        benchmark_id=benchmark_id,
        benchmark_version="1.0.0",
        target_model="gpt-4o",
        evaluation_status=ReportRunStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        overall_score=88.5,
    )
    mock_paginated = PaginatedReportRunsRead(
        items=[mock_entry],
        total=1,
        page=1,
        size=10,
    )
    mock_reporting_service.get_runs_filtered.return_value = mock_paginated

    response = test_client.get(
        "/api/v1/reports/runs",
        params={
            "status": "COMPLETED",
            "target_model": "gpt-4o",
            "benchmark_version": "1.0.0",
            "limit": 10,
            "offset": 0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["run_id"] == str(run_id)

    # Verify that get_runs_filtered was called with an internal ReportRunsFilter
    assert mock_reporting_service.get_runs_filtered.call_count == 1
    filter_arg = mock_reporting_service.get_runs_filtered.call_args[0][0]
    assert isinstance(filter_arg, ReportRunsFilter)
    assert filter_arg.status == ReportRunStatus.COMPLETED
    assert filter_arg.target_model == "gpt-4o"
    assert filter_arg.benchmark_version == "1.0.0"
    assert filter_arg.limit == 10
    assert filter_arg.offset == 0


def test_list_report_runs_validation_error(test_client, mock_reporting_service):
    # limit over 100 should fail validation (le=100)
    response = test_client.get("/api/v1/reports/runs", params={"limit": 999})
    assert response.status_code == 422


def test_openapi_schema_contains_reporting_endpoints(test_client):
    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})
    assert "/api/v1/reports/runs" in paths
    assert "/api/v1/reports/runs/{run_id}" in paths
    assert "/api/v1/reports/models/{model_identifier}/capabilities" in paths
