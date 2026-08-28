"""Tests for AtlasClient.get_benchmark_leaderboard.

Uses ``pytest-httpx`` for mock transport; no live Atlas deployment required.
The benchmark leaderboard endpoint returns ``LeaderboardRead`` directly (not
wrapped in ``APIResponse``), mirroring the execution/report endpoints.
"""

from __future__ import annotations

import json

import httpx
import pytest

from atlas_sdk.client import AtlasClient
from atlas_sdk.errors import (
    AuthError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from atlas_sdk.models.leaderboard import (
    LeaderboardEntryRead,
    LeaderboardRead,
    LeaderboardType,
    ModelBenchmarkHistory,
    ModelSummary,
    TrendPoint,
)


def _err(status: int, code: str = "", message: str = "") -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


def _leaderboard_payload(**overrides: object) -> dict:
    """Realistic bare ``LeaderboardRead`` payload (shape recorded from the live API)."""
    payload: dict = {
        "leaderboard_type": "BENCHMARK",
        "title": "Benchmark Version 1.0.0",
        "description": "Leaderboard for Benchmark Version 1.0.0",
        "benchmark_version_id": "181d1c91-15f9-43e7-866d-33809aaaedf1",
        "capability_id": None,
        "entries": {
            "items": [
                {
                    "rank": 1,
                    "model_name": "mock",
                    "overall_score": 100.0,
                    "benchmark_count": 1,
                    "last_updated": "2026-08-23T07:04:07.219431",
                    "rank_delta": None,
                    "metadata": None,
                },
                {
                    "rank": 2,
                    "model_name": "mock",
                    "overall_score": 100.0,
                    "benchmark_count": 1,
                    "last_updated": "2026-08-23T07:04:07.219431",
                    "rank_delta": 0,
                    "metadata": {"capability_score": 50.0},
                },
            ],
            "total": 2,
            "limit": 20,
            "offset": 0,
            "next_cursor": None,
        },
    }
    payload.update(overrides)
    return payload


def _url(benchmark_version_id: str, *, params: str = "") -> str:
    base = f"http://localhost:8000/api/v1/benchmarks/{benchmark_version_id}/leaderboard"
    return f"{base}?{params}" if params else base


class TestLeaderboardDto:
    """DTO field-for-field contract with the wire payload."""

    def test_models_parse_live_payload_shape(self) -> None:
        raw = json.dumps(_leaderboard_payload())
        leaderboard = LeaderboardRead.model_validate_json(raw)
        assert leaderboard.leaderboard_type is LeaderboardType.BENCHMARK
        assert leaderboard.title == "Benchmark Version 1.0.0"
        assert leaderboard.description == "Leaderboard for Benchmark Version 1.0.0"
        assert leaderboard.benchmark_version_id == "181d1c91-15f9-43e7-866d-33809aaaedf1"
        assert leaderboard.capability_id is None
        assert leaderboard.entries.total == 2
        assert leaderboard.entries.limit == 20
        assert leaderboard.entries.offset == 0
        assert leaderboard.entries.next_cursor is None
        assert len(leaderboard.entries.items) == 2

        first: LeaderboardEntryRead = leaderboard.entries.items[0]
        assert first.rank == 1
        assert first.model_name == "mock"
        assert first.overall_score == 100.0
        assert first.benchmark_count == 1
        assert first.last_updated.isoformat().startswith("2026-08-23T07:04:07")
        assert first.rank_delta is None
        assert first.metadata is None

        second: LeaderboardEntryRead = leaderboard.entries.items[1]
        assert second.rank_delta == 0
        assert second.metadata == {"capability_score": 50.0}

    def test_model_dump_round_trips_wire_shape(self) -> None:
        leaderboard = LeaderboardRead.model_validate(_leaderboard_payload())
        dumped = leaderboard.model_dump(mode="json")
        assert dumped["leaderboard_type"] == "BENCHMARK"
        assert dumped["entries"]["items"][0]["model_name"] == "mock"
        assert dumped["entries"]["total"] == 2


class TestGetBenchmarkLeaderboard:
    _BV_ID = "181d1c91-15f9-43e7-866d-33809aaaedf1"

    def test_success_parses_leaderboard(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=20&offset=0"),
            json=_leaderboard_payload(),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_benchmark_leaderboard(self._BV_ID)
        assert result.leaderboard_type is LeaderboardType.BENCHMARK
        assert result.title == "Benchmark Version 1.0.0"
        assert result.benchmark_version_id == self._BV_ID
        assert len(result.entries.items) == 2
        assert result.entries.total == 2
        assert result.entries.items[0].model_name == "mock"
        assert result.entries.items[0].overall_score == 100.0
        client.close()

    def test_sends_limit_offset_query_params(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=10&offset=5"),
            json=_leaderboard_payload(),
        )
        client = AtlasClient("http://localhost:8000")
        client.get_benchmark_leaderboard(self._BV_ID, limit=10, offset=5)
        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "GET"
        assert request.url.params["limit"] == "10"
        assert request.url.params["offset"] == "5"
        client.close()

    def test_default_limit_is_20(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=20&offset=0"),
            json=_leaderboard_payload(),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_benchmark_leaderboard(self._BV_ID)
        assert result.entries.limit == 20
        client.close()

    def test_empty_entries(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=20&offset=0"),
            json=_leaderboard_payload(
                entries={"items": [], "total": 0, "limit": 20, "offset": 0, "next_cursor": None}
            ),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_benchmark_leaderboard(self._BV_ID)
        assert result.entries.items == []
        assert result.entries.total == 0
        client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=20&offset=0"),
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.get_benchmark_leaderboard(self._BV_ID)
        assert exc_info.value.status == 401
        client.close()

    def test_403_raises_forbidden_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=20&offset=0"),
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError) as exc_info:
            client.get_benchmark_leaderboard(self._BV_ID)
        assert exc_info.value.status == 403
        client.close()

    def test_404_raises_not_found_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=20&offset=0"),
            status_code=404,
            json=_err(404, "NOT_FOUND", "Benchmark version not found."),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError) as exc_info:
            client.get_benchmark_leaderboard(self._BV_ID)
        assert exc_info.value.status == 404
        client.close()

    def test_422_raises_validation_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=20&offset=0"),
            status_code=422,
            json=_err(422, "VALIDATION_ERROR", "Invalid parameters"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError) as exc_info:
            client.get_benchmark_leaderboard(self._BV_ID)
        assert exc_info.value.status == 422
        client.close()

    def test_500_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_url(self._BV_ID, params="limit=20&offset=0"),
            status_code=500,
            json=_err(500, "INTERNAL", "something broke"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.get_benchmark_leaderboard(self._BV_ID)
        client.close()

    def test_network_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.get_benchmark_leaderboard(self._BV_ID)
        client.close()
# -- ModelSummary --------------------------------------------------------


def _summary_payload(**overrides: object) -> dict:
    """Realistic bare ``ModelSummary`` payload (shape recorded from the live API)."""
    payload: dict = {
        "model": "mock",
        "benchmarks": 4,
        "best_rank": 1,
        "average_rank": 1.5,
        "average_score": 85.71428571428571,
        "last_execution": "2026-08-23T07:04:07.219431",
        "latest_delta": None,
    }
    payload.update(overrides)
    return payload


def _summary_url(model_name: str) -> str:
    return f"http://localhost:8000/api/v1/models/{model_name}/summary"


class TestModelSummaryDto:
    """DTO field-for-field contract with the wire payload."""

    def test_models_parse_live_payload_shape(self) -> None:
        raw = json.dumps(_summary_payload())
        summary = ModelSummary.model_validate_json(raw)
        assert summary.model == "mock"
        assert summary.benchmarks == 4
        assert summary.best_rank == 1
        assert summary.average_rank == 1.5
        assert summary.average_score == 85.71428571428571
        assert summary.last_execution.isoformat() == "2026-08-23T07:04:07.219431"
        assert summary.latest_delta is None

    def test_models_parse_unknown_model_payload(self) -> None:
        raw = json.dumps({
            "model": "SuchModelDoesNotExist",
            "benchmarks": 0,
            "best_rank": None,
            "average_rank": None,
            "average_score": None,
            "last_execution": None,
            "latest_delta": None,
        })
        summary = ModelSummary.model_validate_json(raw)
        assert summary.model == "SuchModelDoesNotExist"
        assert summary.benchmarks == 0
        assert summary.best_rank is None
        assert summary.average_rank is None
        assert summary.average_score is None
        assert summary.last_execution is None
        assert summary.latest_delta is None

    def test_model_dump_round_trips_wire_shape(self) -> None:
        summary = ModelSummary.model_validate(_summary_payload())
        dumped = summary.model_dump(mode="json")
        assert dumped["model"] == "mock"
        assert dumped["benchmarks"] == 4
        assert dumped["best_rank"] == 1
        assert dumped["average_rank"] == 1.5
        assert dumped["latest_delta"] is None


class TestGetModelSummary:
    def test_success_parses_summary(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_summary_url("mock"),
            json=_summary_payload(),
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_model_summary("mock")
        assert result.model == "mock"
        assert result.benchmarks == 4
        assert result.best_rank == 1
        assert result.average_rank == 1.5
        assert result.average_score == 85.71428571428571
        assert result.last_execution.isoformat() == "2026-08-23T07:04:07.219431"
        assert result.latest_delta is None
        client.close()

    def test_unknown_model_parses_zeroed_summary(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_summary_url("nope"),
            json={
                "model": "nope",
                "benchmarks": 0,
                "best_rank": None,
                "average_rank": None,
                "average_score": None,
                "last_execution": None,
                "latest_delta": None,
            },
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_model_summary("nope")
        assert result.model == "nope"
        assert result.benchmarks == 0
        assert result.best_rank is None
        client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_summary_url("mock"),
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.get_model_summary("mock")
        assert exc_info.value.status == 401
        client.close()

    def test_403_raises_forbidden_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_summary_url("mock"),
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError) as exc_info:
            client.get_model_summary("mock")
        assert exc_info.value.status == 403
        client.close()

    def test_404_raises_not_found_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_summary_url("mock"),
            status_code=404,
            json=_err(404, "NOT_FOUND", "Model not found."),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError) as exc_info:
            client.get_model_summary("mock")
        assert exc_info.value.status == 404
        client.close()

    def test_422_raises_validation_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_summary_url("mock"),
            status_code=422,
            json=_err(422, "VALIDATION_ERROR", "Invalid parameters"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError) as exc_info:
            client.get_model_summary("mock")
        assert exc_info.value.status == 422
        client.close()

    def test_500_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_summary_url("mock"),
            status_code=500,
            json=_err(500, "INTERNAL", "something broke"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.get_model_summary("mock")
        client.close()

    def test_network_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.get_model_summary("mock")
        client.close()
# -- TrendPoint (model history) -------------------------------------------


def _point_payload(**overrides: object) -> dict:
    """Realistic bare ``TrendPoint`` payload (shape recorded from the live API)."""
    payload: dict = {
        "timestamp": "2026-08-17T16:25:46.342572",
        "score": 0.0,
        "rank": None,
        "benchmark_version": "15f01fef-bd6c-457c-a041-101dbc6c8740",
        "execution_id": "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0",
    }
    payload.update(overrides)
    return payload


def _history_url(model_name: str) -> str:
    return f"http://localhost:8000/api/v1/models/{model_name}/history"


class TestTrendPointDto:
    """DTO field-for-field contract with the wire payload."""

    def test_models_parse_live_payload_shape(self) -> None:
        point = TrendPoint.model_validate(_point_payload())
        assert point.timestamp.isoformat() == "2026-08-17T16:25:46.342572"
        assert point.score == 0.0
        assert point.rank is None
        assert point.benchmark_version == "15f01fef-bd6c-457c-a041-101dbc6c8740"
        assert point.execution_id == "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0"

    def test_models_parse_rank_populated(self) -> None:
        point = TrendPoint.model_validate(
            _point_payload(rank=3, benchmark_version=None)
        )
        assert point.rank == 3
        assert point.benchmark_version is None

    def test_model_dump_round_trips_wire_shape(self) -> None:
        point = TrendPoint.model_validate(_point_payload(score=100.0, rank=2))
        dumped = point.model_dump(mode="json")
        assert dumped["timestamp"] == "2026-08-17T16:25:46.342572"
        assert dumped["score"] == 100.0
        assert dumped["rank"] == 2
        assert dumped["benchmark_version"] == "15f01fef-bd6c-457c-a041-101dbc6c8740"
        assert dumped["execution_id"] == "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0"


class TestGetModelHistory:
    def test_success_parses_list_of_points(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_history_url("mock"),
            json=[
                _point_payload(),
                _point_payload(
                    timestamp="2026-08-23T07:04:07.219431",
                    score=100.0,
                    benchmark_version="181d1c91-15f9-43e7-866d-33809aaaedf1",
                    execution_id="b94248f7-f5f9-4ed8-992a-b29751b4e710",
                ),
            ],
        )
        client = AtlasClient("http://localhost:8000")
        points = client.get_model_history("mock")
        assert len(points) == 2
        assert points[0].timestamp.isoformat() == "2026-08-17T16:25:46.342572"
        assert points[0].score == 0.0
        assert points[1].score == 100.0
        assert points[1].execution_id == "b94248f7-f5f9-4ed8-992a-b29751b4e710"
        client.close()

    def test_unknown_model_parses_empty_list(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(method="GET", url=_history_url("nope"), json=[])
        client = AtlasClient("http://localhost:8000")
        points = client.get_model_history("nope")
        assert points == []
        client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_history_url("mock"),
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.get_model_history("mock")
        assert exc_info.value.status == 401
        client.close()

    def test_403_raises_forbidden_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_history_url("mock"),
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError) as exc_info:
            client.get_model_history("mock")
        assert exc_info.value.status == 403
        client.close()

    def test_404_raises_not_found_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_history_url("mock"),
            status_code=404,
            json=_err(404, "NOT_FOUND", "Model not found."),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(NotFoundError) as exc_info:
            client.get_model_history("mock")
        assert exc_info.value.status == 404
        client.close()

    def test_422_raises_validation_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_history_url("mock"),
            status_code=422,
            json=_err(422, "VALIDATION_ERROR", "Invalid parameters"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ValidationError) as exc_info:
            client.get_model_history("mock")
        assert exc_info.value.status == 422
        client.close()

    def test_500_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_history_url("mock"),
            status_code=500,
json=_err(500, "INTERNAL", "something broke"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.get_model_history("mock")
        client.close()

    def test_network_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.get_model_history("mock")
        client.close()
# -- ModelBenchmarkHistory (model benchmarks) ------------------------------


def _bench_mark_payload(**overrides: object) -> dict:
    """Realistic bare ``ModelBenchmarkHistory`` payload (shape recorded from the live API)."""
    payload: dict = {
        "benchmark_name": "Python Vulnerability Detection Benchmark",
        "versions": [
            {
                "version_string": "1.0.0",
                "history": [
                    {
                        "timestamp": "2026-08-17T16:25:46.342572",
                        "score": 0.0,
                        "rank": None,
                        "benchmark_version": "15f01fef-bd6c-457c-a041-101dbc6c8740",
                        "execution_id": "5cad9594-0f35-4e1f-9c60-cdcbd41d2cd0",
                    },
                    {
                        "timestamp": "2026-08-23T07:04:07.219431",
                        "score": 100.0,
                        "rank": 1,
                        "benchmark_version": "181d1c91-15f9-43e7-866d-33809aaaedf1",
                        "execution_id": "b94248f7-f5f9-4ed8-992a-b29751b4e710",
                    },
                ],
            }
        ],
    }
    payload.update(overrides)
    return payload


def _benchmarks_url(model_name: str) -> str:
    return f"http://localhost:8000/api/v1/models/{model_name}/benchmarks"


class TestModelBenchmarkHistoryDto:
    """DTO field-for-field contract with the wire payload."""

    def test_models_parse_live_payload_shape(self) -> None:
        entry = ModelBenchmarkHistory.model_validate(_bench_mark_payload())
        assert entry.benchmark_name == "Python Vulnerability Detection Benchmark"
        assert len(entry.versions) == 1
        version = entry.versions[0]
        assert version.version_string == "1.0.0"
        assert len(version.history) == 2
        first = version.history[0]
        assert first.timestamp.isoformat() == "2026-08-17T16:25:46.342572"
        assert first.score == 0.0
        assert first.rank is None
        second = version.history[1]
        assert second.score == 100.0
        assert second.rank == 1
        assert second.execution_id == "b94248f7-f5f9-4ed8-992a-b29751b4e710"

    def test_model_dump_round_trips_wire_shape(self) -> None:
        entry = ModelBenchmarkHistory.model_validate(_bench_mark_payload())
        dumped = entry.model_dump(mode="json")
        assert dumped["benchmark_name"] == "Python Vulnerability Detection Benchmark"
        assert dumped["versions"][0]["version_string"] == "1.0.0"
        assert dumped["versions"][0]["history"][1]["score"] == 100.0
        assert dumped["versions"][0]["history"][1]["rank"] == 1


class TestGetModelBenchmarks:
    def test_success_parses_list(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_benchmarks_url("mock"),
            json=[
                _bench_mark_payload(),
                _bench_mark_payload(benchmark_name="HumanEval"),
            ],
        )
        client = AtlasClient("http://localhost:8000")
        result = client.get_model_benchmarks("mock")
        assert len(result) == 2
        assert result[0].benchmark_name == "Python Vulnerability Detection Benchmark"
        assert result[0].versions[0].version_string == "1.0.0"
        assert result[0].versions[0].history[1].score == 100.0
        assert result[1].benchmark_name == "HumanEval"
        client.close()

    def test_unknown_model_parses_empty_list(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(method="GET", url=_benchmarks_url("nope"), json=[])
        client = AtlasClient("http://localhost:8000")
        result = client.get_model_benchmarks("nope")
        assert result == []
        client.close()

    def test_401_raises_auth_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_benchmarks_url("mock"),
            status_code=401,
            json=_err(401, "UNAUTHORIZED", "Token expired"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(AuthError) as exc_info:
            client.get_model_benchmarks("mock")
        assert exc_info.value.status == 401
        client.close()

    def test_403_raises_forbidden_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_benchmarks_url("mock"),
            status_code=403,
            json=_err(403, "FORBIDDEN", "Insufficient permissions"),
        )
        client = AtlasClient("http://localhost:8000")
        with pytest.raises(ForbiddenError) as exc_info:
            client.get_model_benchmarks("mock")
        assert exc_info.value.status == 403
        client.close()

    def test_500_raises_server_error(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=_benchmarks_url("mock"),
            status_code=500,
            json=_err(500, "INTERNAL", "something broke"),
        )
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(ServerError):
            client.get_model_benchmarks("mock")
        client.close()

    def test_network_error_raises_network_error(
        self, httpx_mock: pytest.MockTransport
    ) -> None:
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))
        client = AtlasClient("http://localhost:8000", max_retries=0)
        with pytest.raises(NetworkError):
            client.get_model_benchmarks("mock")
        client.close()
