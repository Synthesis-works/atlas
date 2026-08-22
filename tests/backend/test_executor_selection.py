"""Regression tests for security-review fixes H-1 / M-5 / config validation.

H-1: production must NEVER silently fall back to LocalExecutor.
M-5: benchmark container network modes are allow-listed.
"""

import pytest
from pydantic import ValidationError

from apps.backend.config import Settings
from apps.backend.worker.executor_init import get_executor_for_environment
from packages.execution_engine.application.docker_executor import DockerExecutor
from packages.execution_engine.application.executor import (
    ExecutorRegistry,
    ExecutorUnavailable,
    executor_registry,
)
from packages.execution_engine.application.local_executor import LocalExecutor


@pytest.fixture()
def clean_registry(monkeypatch):
    """Isolate tests from the global registry contents."""
    monkeypatch.setattr(executor_registry, "_executors", {})
    return executor_registry


@pytest.fixture()
def app_settings():
    from apps.backend.config import settings

    return settings


class TestProductionNeverFallsBackToLocal:
    def test_get_default_raises_in_production_without_docker(self, clean_registry, app_settings, monkeypatch):
        monkeypatch.setattr(app_settings, "environment", "production")
        with pytest.raises(ExecutorUnavailable, match="Refusing to fall back"):
            clean_registry.get_default()

    def test_get_default_returns_docker_in_production_when_registered(self, clean_registry, app_settings, monkeypatch):
        monkeypatch.setattr(app_settings, "environment", "production")
        docker_exec = DockerExecutor()
        clean_registry.register(docker_exec)
        assert clean_registry.get_default() is docker_exec

    def test_get_default_prefers_local_in_development(self, clean_registry, app_settings, monkeypatch):
        monkeypatch.setattr(app_settings, "environment", "development")
        local_exec = LocalExecutor()
        clean_registry.register(local_exec)
        assert clean_registry.get_default() is local_exec

    def test_runner_raises_when_explicit_type_missing(self, clean_registry, monkeypatch):
        from apps.backend.worker.execution_runner import ExecutionRunner

        monkeypatch.setenv("ENVIRONMENT", "development")
        runner = ExecutionRunner(db=None, executor_type="docker")  # type: ignore[arg-type]
        with pytest.raises(ExecutorUnavailable, match="explicitly requested"):
            runner._get_executor()

    def test_get_executor_for_environment_rejects_unknown_values(self, app_settings, monkeypatch):
        monkeypatch.setattr(app_settings, "environment", "prod")
        with pytest.raises(ValueError, match="ENVIRONMENT='prod'"):
            get_executor_for_environment()

    def test_get_executor_for_environment_production(self, app_settings, monkeypatch):
        monkeypatch.setattr(app_settings, "environment", "production")
        assert get_executor_for_environment() == "docker"

    def test_settings_validator_rejects_unknown_environment(self):
        with pytest.raises(ValidationError, match="must be 'development' or 'production'"):
            Settings(environment="staging")

    def test_settings_validator_accepts_known_environments(self):
        assert Settings(environment="development").environment == "development"
        assert (
            Settings(environment="production", jwt_secret="x" * 30).environment
            == "production"
        )


class TestNetworkModeAllowlist:
    @pytest.mark.parametrize("mode", ["none", "bridge"])
    def test_builtin_modes_allowed(self, mode):
        assert DockerExecutor(network_mode=mode)._network_mode == mode

    def test_named_user_network_allowed(self):
        assert DockerExecutor(network_mode="atlas-egress")._network_mode == "atlas-egress"

    @pytest.mark.parametrize("mode", ["host", "container:abc123", "none:x"])
    def test_namespace_sharing_modes_rejected(self, mode):
        with pytest.raises(ValueError, match="forbidden|Invalid network mode"):
            DockerExecutor(network_mode=mode)

    def test_env_var_host_is_rejected(self, monkeypatch):
        monkeypatch.setenv("ATLAS_BENCHMARK_NETWORK", "host")
        with pytest.raises(ValueError, match="forbidden"):
            DockerExecutor()

    def test_garbage_rejected(self):
        with pytest.raises(ValueError, match="Invalid network mode"):
            DockerExecutor(network_mode="not a network!")
