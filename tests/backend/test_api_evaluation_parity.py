import uuid
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import (
    get_evaluation_parity_service,
    require_authenticated,
)
from apps.backend.main import app
from apps.backend.services.evaluation_parity import EvaluationParityService


@pytest.fixture
def mock_service():
    return Mock(spec=EvaluationParityService)


@pytest.fixture
def mock_authz_service():
    service = Mock(spec=ProjectAuthorizationService)
    service.authorize_project_access.return_value = Mock(id=uuid.uuid4())
    return service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_token_claims():
    from apps.backend.schemas.auth import TokenClaims

    return TokenClaims(
        sub=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        exp=9999999999,
        iat=1600000000,
        jti=uuid.uuid4(),
    )


@contextmanager
def _override(client, mock_service, mock_authz_service, mock_token_claims):
    app.dependency_overrides[get_evaluation_parity_service] = lambda: mock_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    app.dependency_overrides[require_authenticated] = lambda: mock_token_claims
    yield
    app.dependency_overrides.clear()


def test_get_evaluation_results(client, mock_service, mock_authz_service, mock_token_claims):
    project_id = uuid.uuid4()
    execution_id = uuid.uuid4()

    from apps.backend.schemas.evaluation import EvaluationResultsRead

    mock_service.get_evaluation_results.return_value = EvaluationResultsRead(
        execution_id=execution_id,
        status="completed",
        overall_score=0.85,
        profile_id=uuid.uuid4(),
        total_outputs=4,
        evaluated_outputs=4,
        passed_outputs=3,
    )

    with _override(client, mock_service, mock_authz_service, mock_token_claims):
        resp = client.get(
            f"/api/v1/projects/{project_id}/executions/{execution_id}/evaluation-results"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["execution_id"] == str(execution_id)
    assert body["overall_score"] == 0.85
    assert body["passed_outputs"] == 3


def test_get_evaluation_results_not_found(
    client, mock_service, mock_authz_service, mock_token_claims
):
    project_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    mock_service.get_evaluation_results.return_value = None

    with _override(client, mock_service, mock_authz_service, mock_token_claims):
        resp = client.get(
            f"/api/v1/projects/{project_id}/executions/{execution_id}/evaluation-results"
        )

    assert resp.status_code == 404


def test_create_evaluation_cases(client, mock_service, mock_authz_service, mock_token_claims):
    from apps.backend.schemas.evaluation_cases import (
        EvaluationCaseWriteResponse,
        EvaluationCaseWritten,
    )

    project_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    task_id = uuid.uuid4()
    test_case_id = uuid.uuid4()

    mock_service.create_evaluation_cases.return_value = EvaluationCaseWriteResponse(
        dataset_id=dataset_id,
        written=[
            EvaluationCaseWritten(
                test_case_id=test_case_id,
                task_id=task_id,
                evaluation_method="exact_match",
                expected_answer="42",
            )
        ],
        skipped=0,
    )

    payload = {
        "evaluation_cases": [
            {
                "task_id": str(task_id),
                "test_case_id": str(test_case_id),
                "expected_answer": "42",
                "evaluation_method": "exact_match",
            }
        ]
    }

    with _override(client, mock_service, mock_authz_service, mock_token_claims):
        resp = client.post(
            f"/api/v1/projects/{project_id}/datasets/{dataset_id}/evaluation-cases",
            json=payload,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["written"][0]["expected_answer"] == "42"
    assert body["skipped"] == 0


def test_compare_executions(client, mock_service, mock_authz_service, mock_token_claims):
    from apps.backend.schemas.evaluation import (
        ExecutionCompareItemRead,
        ExecutionCompareResponse,
    )

    project_id = uuid.uuid4()
    e1, e2 = uuid.uuid4(), uuid.uuid4()

    mock_service.compare_executions.return_value = ExecutionCompareResponse(
        leaderboard=[
            ExecutionCompareItemRead(
                execution_id=e1,
                target_model="gpt",
                overall_score=0.9,
                passed_outputs=9,
                total_outputs=10,
                evaluated_outputs=10,
                rank=1,
            ),
            ExecutionCompareItemRead(
                execution_id=e2,
                target_model="claude",
                overall_score=0.8,
                passed_outputs=8,
                total_outputs=10,
                evaluated_outputs=10,
                rank=2,
            ),
        ]
    )

    with _override(client, mock_service, mock_authz_service, mock_token_claims):
        resp = client.post(
            f"/api/v1/projects/{project_id}/executions/compare",
            json={"execution_ids": [str(e1), str(e2)]},
        )

    assert resp.status_code == 200
    leaderboard = resp.json()["leaderboard"]
    assert leaderboard[0]["rank"] == 1
    assert leaderboard[0]["overall_score"] == 0.9


def test_generate_report(client, mock_service, mock_authz_service, mock_token_claims):
    from datetime import datetime

    from atlas_db.models.reporting import Report

    project_id = uuid.uuid4()
    report = Report(project_id=project_id, name="Q1 Report")
    report.id = uuid.uuid4()
    report.created_at = datetime.now()
    report.updated_at = datetime.now()
    report.versions = []
    mock_service.generate_report.return_value = report

    with _override(client, mock_service, mock_authz_service, mock_token_claims):
        resp = client.post(
            f"/api/v1/projects/{project_id}/reports",
            json={"title": "Q1 Report"},
        )

    assert resp.status_code == 201
    assert resp.json()["name"] == "Q1 Report"


def test_generate_report_execution_not_found(
    client, mock_service, mock_authz_service, mock_token_claims
):
    project_id = uuid.uuid4()
    mock_service.generate_report.return_value = None

    with _override(client, mock_service, mock_authz_service, mock_token_claims):
        resp = client.post(f"/api/v1/projects/{project_id}/reports", json={"title": "X"})

    assert resp.status_code == 404


def test_list_reports(client, mock_service, mock_authz_service, mock_token_claims):
    from datetime import datetime

    from atlas_db.models.reporting import Report

    project_id = uuid.uuid4()
    report = Report(project_id=project_id, name="R")
    report.id = uuid.uuid4()
    report.created_at = datetime.now()
    report.updated_at = datetime.now()
    report.versions = []
    mock_service.list_reports.return_value = [report]

    with _override(client, mock_service, mock_authz_service, mock_token_claims):
        resp = client.get(f"/api/v1/projects/{project_id}/reports")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1
