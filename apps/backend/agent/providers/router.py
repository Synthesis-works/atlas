"""
Atlas Agent Provider Router

Production fallback chain (verified 2026-08-15):
    Primary:    Gemini (gemini-3.5-flash-lite)   — Google AI, native functionDeclarations
    Fallback 1: Groq   (llama-3.3-70b-versatile) — Groq.com, OpenAI-compat tool calling
    Fallback 2: Mistral (mistral-small-latest)    — Mistral AI, OpenAI-compat tool calling

xAI/Grok: code preserved in grok.py but EXCLUDED from production chain.
  Reason: account has no credits; grok-2/grok-beta models are deprecated/not found.
  Re-enable by adding GrokAgentProvider() to _build_default_chain() once credits are restored.
"""
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.gemini import GeminiAgentProvider
from apps.backend.agent.providers.groq import GroqAgentProvider
from apps.backend.agent.providers.mistral import MistralAgentProvider
from apps.backend.agent.providers.mock import MockAgentProvider
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """
    Describes a single Agent reasoning provider.

    This is the authoritative source for what the backend exposes to
    GET /api/v1/agent/providers. It reflects static configuration: which
    providers are registered, which model they use, and whether credentials
    are present.

    A live health check with caching should be used separately if
    model-level availability needs to be surfaced in the future.
    """

    value: str          # Identifier sent by the frontend when submitting a task
    label: str          # Human-readable name shown in the UI
    description: str    # Brief description of the provider
    model: str          # Default model ID used for this provider
    is_test_only: bool  # True = never exposed in the user-facing provider selector
    api_key_env: str    # Environment variable that must be present for this provider

    def is_configured(self) -> bool:
        """Returns True if the required API key is set in the environment."""
        if not self.api_key_env:
            return True  # No key required (e.g. Mock)
        return bool(os.getenv(self.api_key_env))


# ---------------------------------------------------------------------------
# Registry of all known providers — single source of truth.
# Order matters: this is the fallback chain priority.
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: list[ProviderConfig] = [
    ProviderConfig(
        value="gemini",
        label="Gemini (Google)",
        description="Google Gemini via Generative Language API. Supports native function calling.",
        model="gemini-3.5-flash-lite",
        is_test_only=False,
        api_key_env="GEMINI_API_KEY",
    ),
    ProviderConfig(
        value="groq",
        label="Groq (LLaMA 3.3)",
        description="LLaMA 3.3 70B via Groq.com inference API. Ultra-low latency tool calling.",
        model="llama-3.3-70b-versatile",
        is_test_only=False,
        api_key_env="GROQ_API_KEY",
    ),
    ProviderConfig(
        value="mistral",
        label="Mistral AI",
        description="Mistral Small via Mistral AI API. Strong reasoning with function calling.",
        model="mistral-small-latest",
        is_test_only=False,
        api_key_env="MISTRAL_API_KEY",
    ),
    # xAI Grok: disabled — no account credits, models deprecated.
    # Re-enable once account is funded and valid model IDs are confirmed.
    # ProviderConfig(
    #     value="grok",
    #     label="Grok (xAI)",
    #     description="xAI Grok reasoning via xAI API.",
    #     model="grok-3-mini",
    #     is_test_only=False,
    #     api_key_env="XAI_API_KEY",
    # ),
    ProviderConfig(
        value="mock",
        label="Atlas Mock (Instant)",
        description="Deterministic rule-based mock provider. No API calls. For testing only.",
        model="mock",
        is_test_only=True,
        api_key_env="",  # No key required
    ),
]


def get_configured_providers(include_test_only: bool = False) -> list[ProviderConfig]:
    """
    Returns providers that are configured (API key present).
    By default excludes test-only providers (i.e. Mock).
    """
    return [
        p for p in PROVIDER_REGISTRY
        if (include_test_only or not p.is_test_only) and p.is_configured()
    ]


def build_provider_instance(provider_value: str, model_override: Optional[str] = None) -> Optional[BaseLLMProvider]:
    """
    Instantiate the agent provider for a given provider value string.
    Returns None if the provider is not recognized.
    """
    config = next((p for p in PROVIDER_REGISTRY if p.value == provider_value), None)
    if config is None:
        return None

    model = model_override or config.model

    if provider_value == "gemini":
        return GeminiAgentProvider(model=model)
    if provider_value == "groq":
        return GroqAgentProvider(model=model)
    if provider_value == "mistral":
        return MistralAgentProvider(model=model)
    if provider_value == "mock":
        return MockAgentProvider()

    return None


def _provider_value(provider: BaseLLMProvider) -> str:
    """Return the registry value (e.g. 'gemini') for a provider instance."""
    return provider.__class__.__name__.replace("AgentProvider", "").lower()


def _build_default_chain() -> list[BaseLLMProvider]:
    """
    Builds the production fallback chain from PROVIDER_REGISTRY.
    Only includes configured (key-present), non-test-only providers in registry order.
    """
    chain = []
    for config in PROVIDER_REGISTRY:
        if config.is_test_only:
            continue
        if not config.is_configured():
            logger.info(f"Provider '{config.value}' skipped in fallback chain — {config.api_key_env} not set.")
            continue
        instance = build_provider_instance(config.value)
        if instance:
            chain.append(instance)
    return chain


class ProviderRouter(BaseLLMProvider):
    """
    Production-grade LLM Provider Router with automatic fallback chain.

    Default chain (when all keys are configured):
        Primary:    GeminiAgentProvider (gemini-3.5-flash-lite)
        Fallback 1: GroqAgentProvider   (llama-3.3-70b-versatile)
        Fallback 2: MistralAgentProvider (mistral-small-latest)

    The chain is built from PROVIDER_REGISTRY at instantiation time,
    so adding or re-enabling a provider only requires editing that registry.
    """

    def __init__(
        self,
        primary: Optional[BaseLLMProvider] = None,
        fallbacks: Optional[list[BaseLLMProvider]] = None,
        max_retries_per_provider: int = 2,
        max_backoff_seconds: float = 5.0,
    ):
        default_chain = _build_default_chain()

        if primary is not None:
            # Explicit primary override — build fallbacks from registry, excluding the
            # provider already being used as primary to avoid double-invocation.
            primary_value = _provider_value(primary)
            registry_fallbacks = [
                p for p in default_chain if _provider_value(p) != primary_value
            ]
            self.primary = primary
            self.fallbacks = fallbacks if fallbacks is not None else registry_fallbacks
        elif default_chain:
            self.primary = default_chain[0]
            self.fallbacks = default_chain[1:]
        else:
            # No providers configured — fail gracefully on first decide() call
            logger.error(
                "ProviderRouter: No providers are configured. "
                "Set at least one of GEMINI_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY."
            )
            self.primary = MockAgentProvider()  # Fail-safe — always returns a result
            self.fallbacks = []

        self.max_retries_per_provider = max_retries_per_provider
        self.max_backoff_seconds = max_backoff_seconds
        self._provider_cooldowns: dict[str, float] = {}

    def _classify_error(self, err_str: str) -> str:
        """
        Classifies error strings into failure categories:
        - 'AUTH': 401/403 credential issues -> fallback to next provider
        - 'FALLBACK': model not found / 400 / 404 / no credits -> fallback immediately
        - 'RETRYABLE': 429 / 5xx / timeout -> retry then fallback
        - 'FATAL': internal schema/state corruption -> fail task
        """
        err_lower = err_str.lower()
        if any(k in err_lower for k in ["401", "403", "unauthorized", "invalid_api_key", "invalid api key"]):
            return "AUTH"
        if any(k in err_lower for k in [
            "model not found", "model unavailable", "unsupported model",
            "invalid_argument", "400", "404", "no credits", "permission-denied",
        ]):
            return "FALLBACK"
        if any(k in err_lower for k in [
            "429", "500", "502", "503", "timeout",
            "resource_exhausted", "connection failure", "request failed",
        ]):
            return "RETRYABLE"
        if any(k in err_lower for k in ["schema_error", "corrupted_state", "invalid_decision"]):
            return "FATAL"
        return "FALLBACK"

    def _record_fallback(
        self,
        task: AgentTask,
        chain: list[BaseLLMProvider],
        provider_idx: int,
        provider_name: str,
        reason: str,
    ) -> None:
        """
        Emit a provider_fallback trace event whenever the router advances the
        chain away from a provider, so the execution trace explains why.
        """
        next_p = chain[provider_idx + 1] if provider_idx + 1 < len(chain) else None
        if next_p is None:
            next_name = "NONE"
        else:
            next_name = getattr(
                next_p,
                "name",
                getattr(
                    next_p,
                    "provider_name",
                    next_p.__class__.__name__.replace("AgentProvider", "").lower(),
                ),
            )
        task.record_trace(
            step=task.step_count,
            action="provider_fallback",
            result={
                "failed_provider": provider_name,
                "next_provider": next_name,
                "reason": reason,
            },
        )

    def decide(
        self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]
    ) -> AgentDecision:
        chain = [self.primary] + self.fallbacks
        failures_summary = []
        now = time.time()

        for provider_idx, provider in enumerate(chain):
            provider_name = getattr(
                provider,
                "name",
                getattr(
                    provider,
                    "provider_name",
                    provider.__class__.__name__.replace("AgentProvider", "").lower(),
                ),
            )
            model_name = getattr(provider, "model", "default")

            # Skip provider if cooling down due to recent error
            cooldown_until = self._provider_cooldowns.get(provider_name, 0)
            if now < cooldown_until:
                remaining_cd = int(cooldown_until - now)
                msg = f"Provider '{provider_name}' skipped (cooldown {remaining_cd}s remaining)."
                logger.info(msg)
                failures_summary.append(f"{provider_name}: Cooldown active ({remaining_cd}s remaining)")
                self._record_fallback(
                    task,
                    chain,
                    provider_idx,
                    provider_name,
                    f"Provider '{provider_name}' skipped due to active cooldown "
                    f"({remaining_cd}s remaining).",
                )
                continue

            # Skip provider if API key is not configured
            client = getattr(provider, "client", None)
            if client and hasattr(client, "health") and not client.health():
                msg = f"Provider '{provider_name}' skipped (unhealthy / missing API key)."
                logger.info(msg)
                failures_summary.append(f"{provider_name}: Unhealthy/Missing Key")
                self._record_fallback(
                    task,
                    chain,
                    provider_idx,
                    provider_name,
                    f"Provider '{provider_name}' skipped (unhealthy / missing API key).",
                )
                continue

            task.current_provider = provider_name

            for attempt in range(self.max_retries_per_provider + 1):
                start_time = time.time()
                try:
                    logger.info(
                        f"Attempting decision with provider '{provider_name}' "
                        f"(model: {model_name}, attempt: {attempt + 1})"
                    )
                    decision = provider.decide(task, prompt_context, available_tools)
                    latency_ms = int((time.time() - start_time) * 1000)

                    if decision.type == AgentDecisionType.FAIL:
                        err_msg = decision.error_message or "Unknown failure"
                        category = self._classify_error(err_msg)

                        if category == "FATAL":
                            logger.error(f"Fatal internal error on provider '{provider_name}': {err_msg}")
                            task.record_trace(
                                step=task.step_count,
                                action=f"provider_fatal_error_{provider_name}",
                                result={"provider": provider_name, "error": err_msg, "fatal": True},
                            )
                            return decision

                        if category in ("AUTH", "FALLBACK"):
                            logger.warning(
                                f"Provider '{provider_name}' {category} error ({err_msg}). Falling back..."
                            )
                            self._provider_cooldowns[provider_name] = time.time() + 120.0
                            failures_summary.append(f"{provider_name}: {err_msg}")
                            self._record_fallback(
                                task, chain, provider_idx, provider_name, err_msg
                            )
                            break

                        # RETRYABLE
                        if attempt < self.max_retries_per_provider:
                            sleep_time = min((attempt + 1) * 2.0, self.max_backoff_seconds)
                            logger.warning(
                                f"Retryable error on '{provider_name}' ({err_msg}). "
                                f"Retrying in {sleep_time}s..."
                            )
                            time.sleep(sleep_time)
                            continue
                        else:
                            self._provider_cooldowns[provider_name] = time.time() + 60.0
                            failures_summary.append(f"{provider_name}: {err_msg}")
                            self._record_fallback(
                                task,
                                chain,
                                provider_idx,
                                provider_name,
                                f"Provider '{provider_name}' exhausted retries "
                                f"({self.max_retries_per_provider}): {err_msg}",
                            )
                            break

                    # Decision succeeded (TOOL_CALL or FINAL_RESPONSE)
                    task.record_trace(
                        step=task.step_count,
                        action=f"provider_decision_{provider_name}",
                        result={
                            "provider": provider_name,
                            "model": model_name,
                            "attempt": attempt + 1,
                            "latency_ms": latency_ms,
                            "decision_type": decision.type.value,
                        },
                    )
                    return decision

                except Exception as e:
                    err_str = str(e)
                    latency_ms = int((time.time() - start_time) * 1000)
                    category = self._classify_error(err_str)

                    if category == "FATAL":
                        logger.error(f"Fatal exception on provider '{provider_name}': {err_str}")
                        return AgentDecision(
                            type=AgentDecisionType.FAIL,
                            error_message=f"Fatal error on provider {provider_name}: {err_str}",
                        )

                    if category in ("AUTH", "FALLBACK"):
                        logger.warning(f"Exception on '{provider_name}' ({err_str}). Falling back...")
                        failures_summary.append(f"{provider_name}: {err_str}")
                        self._record_fallback(
                            task, chain, provider_idx, provider_name, err_str
                        )
                        break

                    if attempt < self.max_retries_per_provider:
                        sleep_time = min((attempt + 1) * 2.0, self.max_backoff_seconds)
                        logger.warning(
                            f"Exception on '{provider_name}' ({err_str}). Retrying in {sleep_time}s..."
                        )
                        time.sleep(sleep_time)
                        continue
                    else:
                        failures_summary.append(f"{provider_name}: {err_str}")
                        self._record_fallback(
                            task,
                            chain,
                            provider_idx,
                            provider_name,
                            f"Provider '{provider_name}' exhausted retries "
                            f"({self.max_retries_per_provider}): {err_str}",
                        )
                        break

        # All providers exhausted
        all_err = "All LLM providers in fallback chain failed: " + "; ".join(failures_summary)
        logger.error(all_err)
        return AgentDecision(
            type=AgentDecisionType.FAIL,
            error_message=all_err,
        )
