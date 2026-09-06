"""Tests for AtlasClient evaluation-parity methods.

Uses ``pytest-httpx`` for mock transport; no live Atlas deployment required.
These endpoints return DTOs directly (not wrapped in ``APIResponse``), mirroring
the execution/report endpoints.
"""

from __future__ import annotations

import httpx
import pytest

from atlas_sdk.client import AtlasClient
from atlas_sdk.errors import (
    AuthError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    ServerError,
)
from atlas_sdk.models.evaluation import (
    EvaluationCaseItem,
    EvaluationEnqueuedRead,
    EvaluationResultsRead,
    ExecutionCompareResponse,
    ReportListRead,
    ReportRead,
)


def _err(status: int, code: str = "", message: str = "") -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


PROJECT = "732bb328-d628-4041-8dad-641436b05afa"
EXEC1 = "b94248f7-f5f9-4ed8-992a-b29751b4e710"
EXEC2 = "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0"


def _results_payload(**overrides: object) -> dict:
    payload: dict = {
        "execution_id": EXEC1,
        "status": "completed",
        "overall_score": 0.85,
        "profile_id": "77777777-7777-7777-7777-777777777777",
        "total_outputs": 3,
        "evaluated_outputs": 3,
        "passed_outputs": 2,
        "results": [
            {
                "model_output_id": "11111111-1111-1111-1111-111111111111",
                "strategy_version_id": "22222222-2222-2222-2222-222222222222",
                "judge_id": None,
                "status": "completed",
                "passed": True,
                "confidence": 0.99,
                "reasoning": None,
                "raw_measurements": None,
            }
        ],
    }
    payload.update(overrides)
    return payload


def _enqueued_payload(**overrides: object) -> dict:
    payload: dict = {
        "execution_id": EXEC1,
        "status": "QUEUED",
        "message": "Evaluation task enqueued successfully",
    }
    payload.update(overrides)
    return payload


def _compare_url() -> str:
    return f"http://localhost:8000/api/v1/projects/{PROJECT}/executions/compare"


def _results_url() -> str:
    return f"http://localhost:8000/api/v1/projects/{PROJECT}/executions/{EXEC1}/evaluation-results"


class TestEvaluationDtos:
    def test_evaluation_results_parse(self) -> None:
        result = EvaluationResultsRead.model_validate(_results_payload())
        assert str(result.execution_id) == EXEC1
        assert result.overall_score == 0.85
        assert result.evaluated_outputs == 3
        assert result.passed_outputs == 2
        assert len(result.results) == 1
        assert result.results[0].passed is True

    def test_enqueued_parse(self) -> None:
        enqueued = EvaluationEnqueuedRead.model_validate(_enqueued_payload())
        assert enqueued.status == "QUEUED"
        assert str(enqueued.execution_id) == EXEC1


class TestEnqueueEvaluation:
    def test_success(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=(f"http://localhost:8000/api/v1/projects/{PROJECT}/executions/{EXEC1}/evaluate"),
            status_code=202,
            json=_enqueued_payload(),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.enqueue_evaluation(PROJECT, EXEC1)
        assert result.status == "QUEUED"
        assert str(result.execution_id) == EXEC1
        client.close()

    def test_403_raises_forbidden(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=(f"http://localhost:8000/api/v1/projects/{PROJECT}/executions/{EXEC1}/evaluate"),
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError):
            client.enqueue_evaluation(PROJECT, EXEC1)
        client.close()


class TestGetEvaluationResults:
    def test_success(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(method="GET", url=_results_url(), json=_results_payload())
        client = AtlasClient("http://localhost:8000")
        result = client.get_evaluation_results(PROJECT, EXEC1)
        assert isinstance(result, EvaluationResultsRead)
        assert result.overall_score == 0.85
        assert result.passed_outputs == 2
        client.close()

    def test_404_raises_not_found(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_results_url(),
            status_code=404,
            json=_err(404, "NOT_FOUND", "Execution not found in this project."),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError):
            client.get_evaluation_results(PROJECT, EXEC1)
        client.close()


class TestCreateEvaluationCases:
    def test_success(self, httpx_mock: pytest.MockTransport) -> None:
        url = (
            f"http://localhost:8000/api/v1/projects/{PROJECT}"
            "/datasets/33333333-3333-3333-3333-333333333333/evaluation-cases"
        )
        httpx_mock.add_response(
            method="POST",
            url=url,
            status_code=201,
            json={
                "dataset_id": "33333333-3333-3333-3333-333333333333",
                "written": [
                    {
                        "test_case_id": "44444444-4444-4444-4444-444444444444",
                        "task_id": "55555555-5555-5555-5555-555555555555",
                        "evaluation_method": "exact_match",
                        "expected_answer": "42",
                    }
                ],
                "skipped": 0,
            },
        )
        case = EvaluationCaseItem(
            task_id="55555555-5555-5555-5555-555555555555",
            test_case_id="44444444-4444-4444-4444-444444444444",
            expected_answer="42",
            evaluation_method="exact_match",
        )
        client = AtlasClient("http://localhost:8000")
        result = client.create_evaluation_cases(
            PROJECT, "33333333-3333-3333-3333-333333333333", [case]
        )
        assert result.skipped == 0
        assert result.written[0].expected_answer == "42"
        client.close()


class TestCompareExecutions:
    def test_success(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=_compare_url(),
            json={
                "leaderboard": [
                    {
                        "execution_id": EXEC1,
                        "target_model": "gemini",
                        "overall_score": 0.9,
                        "passed_outputs": 9,
                        "total_outputs": 10,
                        "evaluated_outputs": 10,
                        "rank": 1,
                    },
                    {
                        "execution_id": EXEC2,
                        "target_model": "claude",
                        "overall_score": 0.8,
                        "passed_outputs": 8,
                        "total_outputs": 10,
                        "evaluated_outputs": 10,
                        "rank": 2,
                    },
                ]
            },
        )
        client = AtlasClient("http://localhost:8000")
        result = client.compare_executions(PROJECT, [EXEC1, EXEC2])
        assert isinstance(result, ExecutionCompareResponse)
        assert result.leaderboard[0].rank == 1
        assert result.leaderboard[0].overall_score == 0.9
        assert result.leaderboard[1].rank == 2
        client.close()


class TestGenerateReport:
    def test_success(self, httpx_mock: pytest.MockTransport) -> None:
        url = f"http://localhost:8000/api/v1/projects/{PROJECT}/reports"
        httpx_mock.add_response(
            method="POST",
            url=url,
            status_code=201,
            json={
                "id": "66666666-6666-6666-6666-666666666666",
                "project_id": PROJECT,
                "name": "Q1 Report",
                "created_at": "2026-09-01T12:00:00Z",
                "updated_at": "2026-09-01T12:00:00Z",
                "versions": [],
            },
        )
        client = AtlasClient("http://localhost:8000")
        result = client.generate_report(PROJECT, "Q1 Report")
        assert isinstance(result, ReportRead)
        assert result.name == "Q1 Report"
        client.close()

    def test_404_raises_not_found(self, httpx_mock: pytest.MockTransport) -> None:
        url = f"http://localhost:8000/api/v1/projects/{PROJECT}/reports"
        httpx_mock.add_response(
            method="POST",
            url=url,
            status_code=404,
            json=_err(404, "NOT_FOUND", "Execution not found in this project."),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError):
            client.generate_report(PROJECT, "Q1 Report", execution_id=EXEC1)
        client.close()


class TestListReports:
    def test_success(self, httpx_mock: pytest.MockTransport) -> None:
        url = f"http://localhost:8000/api/v1/projects/{PROJECT}/reports"
        httpx_mock.add_response(
            method="GET",
            url=url,
            json={
                "project_id": PROJECT,
                "total": 1,
                "reports": [
                    {
                        "id": "66666666-6666-6666-6666-666666666666",
                        "project_id": PROJECT,
                        "name": "Q1 Report",
                        "created_at": "2026-09-01T12:00:00Z",
                        "updated_at": "2026-09-01T12:00:00Z",
                        "versions": [],
                    }
                ],
            },
        )
        client = AtlasClient("http://localhost:8000")
        result = client.list_reports(PROJECT)
        assert isinstance(result, ReportListRead)
        assert result.total == 1
        assert result.reports[0].name == "Q1 Report"
        client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        url = f"http://localhost:8000/api/v1/projects/{PROJECT}/reports"
        httpx_mock.add_response(
            method="GET",
            url=url,
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError):
            client.list_reports(PROJECT)
        client.close()


class TestNetworkError:
    def test_500_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_results_url(),
            status_code=500,
            json=_err(500, "INTERNAL", "boom"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.get_evaluation_results(PROJECT, EXEC1)
        client.close()

    def test_connect_error_raises_network_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.get_evaluation_results(PROJECT, EXEC1)
        client.close()
