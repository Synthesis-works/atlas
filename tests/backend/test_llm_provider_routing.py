"""
Regression tests for explicit LLM provider routing (Finding 7).

Previously `ProviderAdapter.resolve_provider_and_model` silently routed ANY
unresolved model to a local Ollama instance whenever Ollama reported healthy,
and also fell back to Ollama for `mistral-*` models when the Mistral cloud
client was unreachable. A misconfigured target model must now fail loudly
instead of being executed by the wrong architecture.
"""

import pytest

from packages.llm.clients.adapter import ProviderAdapter


@pytest.fixture
def adapter():
    return ProviderAdapter()


@pytest.fixture
def patch_registry(monkeypatch):
    def _patch(models: list[dict]):
        monkeypatch.setattr(
            "packages.llm.registry.ModelRegistry.get_all_models",
            staticmethod(lambda: models),
        )

    return _patch


def test_unresolved_model_does_not_silently_fall_back_to_ollama(
    adapter, patch_registry, monkeypatch
):
    """An unknown model must raise, even when a local Ollama is healthy."""
    monkeypatch.setattr(adapter.clients["ollama"], "health", lambda: True)
    patch_registry([])

    with pytest.raises(ValueError, match="Unsupported target model"):
        adapter.resolve_provider_and_model("qwen2.5-coder:7b")


def test_explicit_ollama_prefix_always_resolves(adapter, patch_registry):
    """An explicit ollama/ prefix is honored regardless of discovery."""
    patch_registry([])
    provider, model = adapter.resolve_provider_and_model("ollama/qwen2.5-coder:7b")
    assert provider == "ollama"
    assert model == "qwen2.5-coder:7b"


def test_registry_registered_model_resolves_to_its_declared_provider(adapter, patch_registry):
    """Models present in the ModelRegistry resolve to their declared provider."""
    patch_registry(
        [
            {
                "provider": "gemini",
                "model": "gemini-3.5-flash-lite",
            }
        ]
    )
    provider, model = adapter.resolve_provider_and_model("gemini-3.5-flash-lite")
    assert provider == "gemini"
    assert model == "gemini-3.5-flash-lite"


def test_mistral_resolves_to_mistral_cloud_even_with_unhealthy_client(
    adapter, patch_registry, monkeypatch
):
    """
    'mistral-*' targets must always resolve to the Mistral cloud client.
    No silent re-routing to Ollama when the Mistral client is unhealthy:
    availability is enforced at generation time via 'get_client' health checks.
    """
    patch_registry([])
    monkeypatch.setattr(adapter.clients["mistral"], "health", lambda: False)
    monkeypatch.setattr(adapter.clients["ollama"], "health", lambda: True)

    provider, model = adapter.resolve_provider_and_model("mistral-small-latest")
    assert provider == "mistral"
    assert model == "mistral-small-latest"
