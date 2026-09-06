"""Tests for health / system DTOs."""

from __future__ import annotations

from atlas_sdk.models.health import HealthData, LivenessResponse, ReadinessResponse


class TestHealthData:
    def test_parse(self) -> None:
        data = {"status": "healthy", "version": "0.9.0"}
        model = HealthData.model_validate(data)
        assert model.status == "healthy"
        assert model.version == "0.9.0"


class TestLivenessResponse:
    def test_parse(self) -> None:
        data = {"status": "alive", "version": "0.9.0"}
        model = LivenessResponse.model_validate(data)
        assert model.status == "alive"
        assert model.version == "0.9.0"


class TestReadinessResponse:
    def test_parse_with_checks(self) -> None:
        data = {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}
        model = ReadinessResponse.model_validate(data)
        assert model.status == "ready"
        assert model.checks["database"] == "ok"
        assert model.checks["redis"] == "ok"

    def test_parse_minimal(self) -> None:
        data = {"status": "not_ready"}
        model = ReadinessResponse.model_validate(data)
        assert model.status == "not_ready"
        assert model.checks == {}
