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
