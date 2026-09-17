"""Execution-target model catalog (Slice 7).

The catalog enumerates the target-model strings ``run submit --target-model``
accepts for THIS deployment.  It derives from the same inputs the execution
path uses — the provider clients registered in ``ProviderAdapter`` (mixing in
the per-provider ``config/providers.json`` overrides) — so the catalog, the
resolver, and runtime availability can never disagree.

Availability (``status``) mirrors the exact gate ``RealModelAdapter.predict``
applies: ``client.health()`` (key present for cloud providers, live host ping
for ollama).  Model-level existence on a provider's API is not verified — the
client layer itself does not check it before ``generate()``.
"""

from __future__ import annotations

import json
import os

from apps.backend.schemas.models import ModelRead, ModelStatus
from packages.llm.clients.adapter import ProviderAdapter

# App-code-referenced execution defaults that the provider clients' static
# ``list_models()`` claims do not necessarily include.  Explicit and documented
# so the catalog cannot silently miss what Atlas itself submits by default:
#   - "gemini-2.5-flash"          SDK / CLI ``run submit`` default target_model
#   - "groq/llama-3.1-8b-instant"  server-side submit fallback (executions.py)
DEFAULT_TARGET_MODELS: tuple[str, ...] = (
    "gemini-2.5-flash",
    "groq/llama-3.1-8b-instant",
)

_PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "mock": "Mock",
    "ollama": "Ollama",
    "gemini": "Gemini",
    "grok": "Grok",
    "mistral": "Mistral",
    "groq": "Groq",
    "nvidia": "Nvidia",
}

# Canonical display order: mock first, then providers in client-table order.
_PROVIDER_ORDER: tuple[str, ...] = (
    "mock",
    "ollama",
    "gemini",
    "grok",
    "mistral",
    "groq",
    "nvidia",
)


def _provider_display_name(provider: str) -> str:
    return _PROVIDER_DISPLAY_NAMES.get(provider, provider)


def _provider_config_models() -> dict[str, str]:
    """Return ``{provider: configured_model}`` from ``config/providers.json``.

    ``ProviderAdapter._load_providers`` reads the same file for its
    ``base_url``/``api_key_env`` per-provider overrides.  The per-provider
    ``model`` field names the model this deployment intends to run; it is
    surfaced here even though execution resolves any legal target string at
    submit time.
    """
    path = os.path.join("config", "providers.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            providers = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(providers, dict):
        return {}
    return {
        str(key): str(conf["model"])
        for key, conf in providers.items()
        if isinstance(conf, dict) and isinstance(conf.get("model"), str)
    }


def list_models(adapter: ProviderAdapter | None = None) -> list[ModelRead]:
    """Build the execution-target model catalog for this deployment.

    ``adapter`` may be injected for tests; otherwise a fresh
    ``ProviderAdapter`` is constructed — the exact same client table the
    execution path uses.
    """
    adapter = adapter or ProviderAdapter()

    ids_by_provider: dict[str, set[str]] = {}

    def register(provider: str, model: str) -> None:
        """Register ``model`` under ``provider``, normalizing any leading
        ``provider/`` the client's static list already carries so canonical ids
        never duplicate the prefix (``groq/groq/x`` is invalid: the resolver
        would mis-parse it)."""
        model = model[len(provider) + 1 :] if model.startswith(f"{provider}/") else model
        if not model:
            return
        ids_by_provider.setdefault(provider, set()).add(model)

    # mock is the test-only target, always available.
    register("mock", "mock")

    configured_models = _provider_config_models()

    for provider, client in adapter.clients.items():
        if provider == "mock":
            continue
        try:
            listed = client.list_models()
        except Exception:
            listed = []
        for entry in listed:
            name = getattr(entry, "name", entry)
            if isinstance(name, str):
                register(provider, name)
        if provider in configured_models:
            register(provider, configured_models[provider])

    for default in DEFAULT_TARGET_MODELS:
        try:
            resolved_provider, _ = adapter.resolve_provider_and_model(default)
        except ValueError:
            continue
        register(resolved_provider, default)

    health_by_provider: dict[str, bool] = {
        provider: client.health() for provider, client in adapter.clients.items()
    }
    health_by_provider.setdefault("mock", True)

    catalog: list[ModelRead] = []
    for provider in _PROVIDER_ORDER:
        available = health_by_provider.get(provider, False)
        is_test_only = provider == "mock"
        for model in sorted(ids_by_provider.get(provider, set())):
            catalog.append(
                ModelRead(
                    id="mock" if is_test_only else f"{provider}/{model}",
                    provider=provider,
                    display_name=(
                        "Mock" if is_test_only else f"{_provider_display_name(provider)} {model}"
                    ),
                    status=ModelStatus.AVAILABLE if available else ModelStatus.NOT_CONFIGURED,
                    is_test_only=is_test_only,
                )
            )
    return catalog
