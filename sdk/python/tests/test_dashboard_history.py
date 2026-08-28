"""Tests for AtlasClient dashboard + recent-activity endpoints.

Uses ``pytest-httpx`` for mock transport; no live Atlas deployment required.
``/api/v1/dashboard`` returns a bare dict; ``/api/v1/history/*/recent``
responses are wrapped in ``APIResponse``.
"""

from __future__ import annotations

import httpx
import pytest

from atlas_sdk.client import AtlasClient
from atlas_sdk.errors import (
    AuthError,
    ForbiddenError,
    NetworkError,
    ServerError,
    ValidationError,
)
from atlas_sdk.models.dashboard import (
    DashboardCapability,
    DashboardSnapshot,
)


def _err(status: int, code: str = "", message: str = "") -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


def _ok(data: dict | list, *, message: str = "Request processed successfully") -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


def _dashboard_payload(**overrides: object) -> dict:
    """Realistic bare dashboard payload (shape recorded from the live API)."""
    payload: dict = {
        "generated_at": "2026-08-28T06:54:40.932356+00:00",
        "version": "1.0.0",
        "summary": {
            "active_runs_count": 6,
            "queued_runs_count": 6,
            "completed_runs_count": 72,
            "failed_runs_count": 19,
            "cancelled_runs_count": 12,
            "total_runs_count": 115,
        },
        "hierarchy": {
            "models": 17,
            "benchmarks": 20,
            "datasets": 14,
            "evaluations": 54,
            "reports": 18,
        },
        "running_jobs": [],
        "recent_verified_runs": [
            {
                "id": "89832d92-424c-459e-b8f7-5a8d0e22be24",
                "model": "gemini-2.0-flash",
                "benchmark": "MBPP",
                "status": "Completed",
                "progress": 100,
                "is_verified": True,
                "source": "real",
            }
        ],
        "active_executions": [
            {
                "id": "ff0a7a03-ca03-4b67-bc47-eae9335ad6e8",
                "model": "gemini-2.5-flash",
                "benchmark": "HellaSwag",
                "status": "Failed",
                "progress": 0,
                "is_verified": False,
                "source": "real",
            }
        ],
        "activity": [
            {
                "id": "ex-ff0a7a03-ca03-4b67-bc47-eae9335ad6e8",
                "type": "evaluation_started",
                "title": "gemini-2.5-flash started on HellaSwag",
                "description": "Run ff0a7a03-ca03-4b67-bc47-eae9335ad6e8 is currently Failed.",
                "timestamp": "2026-08-26T06:24:31.588819+00:00",
            }
        ],
        "runtime": {
            "engine_status": "healthy",
            "total_benchmarks": 20,
            "total_evaluations": 54,
            "total_models": 17,
            "avg_runtime_sec": 13.0,
        },
        "capability": {
            "model_name": "gemini-1.5-pro",
            "provider": "Google AI",
            "rank": 1,
            "score": 84.5,
            "capabilities": [{"domain": "coding", "score": 84.5}],
        },
    }
    payload.update(overrides)
    return payload


class TestDashboardSnapshotDto:
    """DTO field-for-field contract with the wire payload."""

    def test_models_parse_live_payload_shape(self) -> None:
        snapshot = DashboardSnapshot.model_validate(_dashboard_payload())
        assert snapshot.version == "1.0.0"
        assert snapshot.summary.total_runs_count == 115
        assert snapshot.summary.completed_runs_count == 72
        assert snapshot.summary.active_runs_count == 6
        assert snapshot.hierarchy.models == 17
        assert snapshot.hierarchy.benchmarks == 20
        assert snapshot.hierarchy.datasets == 14
        assert snapshot.runtime.engine_status == "healthy"
        assert snapshot.runtime.avg_runtime_sec == 13.0
        assert len(snapshot.recent_verified_runs) == 1
        run = snapshot.recent_verified_runs[0]
        assert run.model == "gemini-2.0-flash"
        assert run.progress == 100
        assert run.is_verified is True
        assert snapshot.active_executions[0].benchmark == "HellaSwag"
        activity = snapshot.activity[0]
        assert activity.type == "evaluation_started"
        assert activity.title == "gemini-2.5-flash started on HellaSwag"
        assert isinstance(snapshot.capability, DashboardCapability)
        assert snapshot.capability is not None
        assert snapshot.capability.model_name == "gemini-1.5-pro"
        assert snapshot.capability.provider == "Google AI"
        assert snapshot.capability.capabilities[0].domain == "coding"
        assert snapshot.capability.capabilities[0].score == 84.5

    def test_models_parse_capability_absent(self) -> None:
        snapshot = DashboardSnapshot.model_validate(
            _dashboard_payload(capability=None)
        )
        assert snapshot.capability is None

    def test_model_dump_round_trips_wire_shape(self) -> None:
        snapshot = DashboardSnapshot.model_validate(_dashboard_payload())
        dumped = snapshot.model_dump(mode="json")
        assert dumped["summary"]["total_runs_count"] == 115
        assert dumped["hierarchy"]["models"] == 17
        assert dumped["activity"][0]["type"] == "evaluation_started"
        assert dumped["runtime"]["avg_runtime_sec"] == 13.0
        assert dumped["capability"]["model_name"] == "gemini-1.5-pro"


class TestGetDashboard:
    def test_success_parses_snapshot(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/dashboard",
            json=_dashboard_payload(),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_dashboard()
        assert result.version == "1.0.0"
        assert result.summary.total_runs_count == 115
        assert result.summary.failed_runs_count == 19
        assert result.hierarchy.evaluations == 54
        assert len(result.activity) == 1
        client.close()

    def test_malformed_payload_raises_validation_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/dashboard",
            json={"unexpected": "format"},
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError):
            client.get_dashboard()
        client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/dashboard",
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.get_dashboard()
        assert exc_info.value.status == 401
        client.close()

    def test_403_raises_forbidden_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/dashboard",
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError) as exc_info:
            client.get_dashboard()
        assert exc_info.value.status == 403
        client.close()

    def test_500_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/dashboard",
            status_code=500,
            json=_err(500, "INTERNAL", "something broke"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.get_dashboard()
        client.close()

    def test_network_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.get_dashboard()
        client.close()


class TestGetRecentBenchmarks:
    def test_success_parses_wrapped_list(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/history/benchmarks/recent?limit=10",
            json=_ok([
                {
                    "id": "c711da4c-dbe9-4b37-a94f-0590ade5d01b",
                    "project_id": "33333333-3333-3333-3333-333333333333",
                    "state": "published",
                    "name": "SWE-Bench Lite",
                }
            ]),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_recent_benchmarks()
        assert len(result) == 1
        assert result[0].name == "SWE-Bench Lite"
        assert result[0].state == "published"
        client.close()

    def test_passes_explicit_limit(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/history/benchmarks/recent?limit=3",
            json=_ok([]),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_recent_benchmarks(limit=3)
        assert result == []
        request = httpx_mock.get_request()
        assert request is not None
        assert request.url.params["limit"] == "3"
        client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/history/benchmarks/recent?limit=10",
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.get_recent_benchmarks()
        assert exc_info.value.status == 401
        client.close()


class TestGetRecentExecutions:
    def test_success_parses_wrapped_list(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/history/executions/recent?limit=10",
            json=_ok([
                {
                    "id": "ff0a7a03-ca03-4b67-bc47-eae9335ad6e8",
                    "benchmark_name": "HellaSwag",
                    "target_model": "gemini-2.5-flash",
                    "status": "FAILED",
                    "started_at": "2026-08-26T06:24:31.588819",
                    "completed_at": "2026-08-26T06:24:39.671965",
                    "duration": 8083,
                    "project_id": "00000000-0000-0000-0000-000000000003",
                }
            ]),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_recent_executions()
        assert len(result) == 1
        execution = result[0]
        assert execution.target_model == "gemini-2.5-flash"
        assert execution.benchmark_name == "HellaSwag"
        assert execution.status.value == "FAILED"
        assert execution.duration == 8083
        assert execution.started_at is not None
        client.close()

    def test_422_raises_validation_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/history/executions/recent?limit=10",
            status_code=422,
            json=_err(422, "VALIDATION_ERROR", "Invalid parameters"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError) as exc_info:
            client.get_recent_executions()
        assert exc_info.value.status == 422
        client.close()


class TestGetRecentModels:
    def test_success_parses_wrapped_list(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/history/models/recent?limit=10",
            json=_ok([
                {
                    "name": "gemini-2.5-flash",
                    "last_executed_at": "2026-08-26T06:24:30.396401",
                    "execution_count": 1,
                },
                {
                    "name": "gemini-1.5-pro",
                    "last_executed_at": "2026-08-26T03:16:42.457915",
                    "execution_count": 12,
                },
            ]),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_recent_models()
        assert len(result) == 2
        assert result[0].name == "gemini-2.5-flash"
        assert result[0].execution_count == 1
        assert result[1].execution_count == 12
        assert result[1].last_executed_at is not None
        client.close()

    def test_network_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.get_recent_models()
        client.close()
