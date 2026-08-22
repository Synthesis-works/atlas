"""Unit tests for DockerExecutor configuration logic.

These tests cover pure configuration behavior that does NOT require a Docker
daemon: network-mode resolution and provider-key allow-list injection.
"""

import os
import uuid
from unittest.mock import patch

from packages.execution_engine.application.docker_executor import DockerExecutor
from packages.execution_engine.application.executor import ExecutionContext


def _context() -> ExecutionContext:
    return ExecutionContext(
        execution_id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        attempt_number=1,
        target_model="test-model",
        benchmark_version_id=uuid.uuid4(),
        dataset_version_id=uuid.uuid4(),
        test_cases=[],
        execution_config={},
    )


class TestNetworkModeResolution:
    def test_defaults_to_none(self):
        with patch.dict(os.environ, {"ATLAS_BENCHMARK_NETWORK": ""}, clear=False):
            executor = DockerExecutor()
            assert executor._network_mode == "none"

    def test_env_var_selects_bridge(self):
        env = {"ATLAS_BENCHMARK_NETWORK": "bridge"}
        with patch.dict(os.environ, env, clear=False):
            executor = DockerExecutor()
            assert executor._network_mode == "bridge"

    def test_explicit_argument_wins_over_env(self):
        env = {"ATLAS_BENCHMARK_NETWORK": "bridge"}
        with patch.dict(os.environ, env, clear=False):
            executor = DockerExecutor(network_mode="none")
            assert executor._network_mode == "none"

    def test_env_var_whitespace_is_ignored(self):
        env = {"ATLAS_BENCHMARK_NETWORK": "   "}
        with patch.dict(os.environ, env, clear=False):
            executor = DockerExecutor()
            assert executor._network_mode == "none"


class TestProviderKeyAllowlist:
    @staticmethod
    def _blank_ambient_keys() -> dict[str, str]:
        """Blank allow-listed names so a loaded developer .env cannot leak in."""
        return {name: "" for name in DockerExecutor.PROVIDER_KEY_ALLOWLIST}

    def test_only_allowlisted_keys_injected(self):
        env = self._blank_ambient_keys()
        env.update(
            {
                "GEMINI_API_KEY": "gemini-secret",
                "DATABASE_URL": "postgresql://super:secret@db/prod",
                "JWT_SECRET": "jwt-secret",
                "STRIPE_API_KEY": "sk_live_danger",
                "OPENAI_API_KEY": "openai-secret",
            }
        )
        with patch.dict(os.environ, env, clear=False):
            injected = DockerExecutor()._provider_env()

        assert injected == {
            "GEMINI_API_KEY": "gemini-secret",
            "OPENAI_API_KEY": "openai-secret",
        }

    def test_no_keys_present_yields_empty_env(self):
        env = self._blank_ambient_keys()
        env["DATABASE_URL"] = "postgresql://x"
        with patch.dict(os.environ, env):
            injected = DockerExecutor()._provider_env()
        assert injected == {}

    def test_container_env_never_contains_db_or_billing_secrets(self):
        """End-to-end guard on _build_container_config's env dict."""
        env = {
            "GEMINI_API_KEY": "gemini-secret",
            "DATABASE_URL": "postgresql://super:secret@db/prod",
            "STRIPE_API_KEY": "sk_live_danger",
            "PAYPAL_CLIENT_SECRET": "pp-danger",
            "JWT_SECRET": "jwt-secret",
        }
        executor = DockerExecutor(image="python:3.11-alpine")
        # create_host_config needs a docker client; stub it out.
        executor._client = type(
            "_StubClient",
            (),
            {"api": type("_StubApi", (), {"create_host_config": staticmethod(lambda **kw: {})})()},
        )()

        with patch.dict(os.environ, env, clear=False):
            config = executor._build_container_config(_context())

        container_env = config["environment"]
        joined = str(container_env)
        assert "gemini-secret" in joined  # allow-listed key present
        for secret in ("postgresql://super:secret", "sk_live_danger", "pp-danger", "jwt-secret"):
            assert secret not in joined

    def test_containers_carry_benchmark_label_for_orphan_pruning(self):
        executor = DockerExecutor(image="python:3.11-alpine")
        executor._client = type(
            "_StubClient",
            (),
            {"api": type("_StubApi", (), {"create_host_config": staticmethod(lambda **kw: {})})()},
        )()
        config = executor._build_container_config(_context())
        assert config["labels"] == {"atlas.benchmark": "true"}
