import datetime
import logging
import time
from typing import Any, Dict, List, Optional

from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.gemini import GeminiAgentProvider
from apps.backend.agent.providers.grok import GrokAgentProvider
from apps.backend.agent.providers.mistral import MistralAgentProvider
from apps.backend.agent.providers.mock import MockAgentProvider
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask

logger = logging.getLogger(__name__)


class ProviderRouter(BaseLLMProvider):
    """
    Production-grade LLM Provider Router with automatic fallback chain:
    Primary: Gemini -> Fallback 1: Grok -> Fallback 2: Mistral
    Note: MockAgentProvider is strictly excluded from production fallback chain.
    """

    def __init__(
        self,
        primary: Optional[BaseLLMProvider] = None,
        fallbacks: Optional[List[BaseLLMProvider]] = None,
        max_retries_per_provider: int = 2,
        max_backoff_seconds: float = 5.0,
    ):
        self.primary = primary or GeminiAgentProvider()
        self.fallbacks = fallbacks if fallbacks is not None else [
            GrokAgentProvider(),
            MistralAgentProvider(),
        ]
        self.max_retries_per_provider = max_retries_per_provider
        self.max_backoff_seconds = max_backoff_seconds

    def _is_fatal_error(self, err_str: str) -> bool:
        """Identifies fatal errors (401/403 auth, 400 bad request, schema error) that should not be retried."""
        fatal_keywords = [
            "401", "403", "unauthorized", "invalid_api_key", "invalid api key",
            "400", "bad request", "invalid_argument", "schema_error"
        ]
        err_lower = err_str.lower()
        return any(k in err_lower for k in fatal_keywords)

    def decide(self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]) -> AgentDecision:
        chain = [self.primary] + self.fallbacks
        failures_summary = []

        for provider_idx, provider in enumerate(chain):
            provider_name = getattr(
                provider,
                "name",
                getattr(provider, "provider_name", provider.__class__.__name__.replace("AgentProvider", "").lower()),
            )
            model_name = getattr(provider, "model", "default")

            # Skip provider if API key is not configured (unless it's mock in test mode)
            client = getattr(provider, "client", None)
            if client and hasattr(client, "health") and not client.health():
                msg = f"Provider '{provider_name}' skipped (unhealthy / missing API key)."
                logger.info(msg)
                failures_summary.append(f"{provider_name}: Unhealthy/Missing Key")
                continue

            task.current_provider = provider_name

            for attempt in range(self.max_retries_per_provider + 1):
                start_time = time.time()
                try:
                    logger.info(f"Attempting decision with provider '{provider_name}' (model: {model_name}, attempt: {attempt + 1})")
                    decision = provider.decide(task, prompt_context, available_tools)

                    latency_ms = int((time.time() - start_time) * 1000)

                    if decision.type == AgentDecisionType.FAIL:
                        err_msg = decision.error_message or "Unknown failure"
                        if self._is_fatal_error(err_msg):
                            logger.error(f"Fatal error encountered on provider '{provider_name}': {err_msg}")
                            # Record telemetry
                            task.record_trace(
                                step=task.step_count,
                                action=f"provider_fatal_error_{provider_name}",
                                result={"provider": provider_name, "error": err_msg, "fatal": True},
                            )
                            return decision

                        # Transient failure, attempt retry or fallback
                        if attempt < self.max_retries_per_provider:
                            sleep_time = min((attempt + 1) * 2.0, self.max_backoff_seconds)
                            logger.warning(f"Transient failure on '{provider_name}' ({err_msg}). Retrying in {sleep_time}s...")
                            time.sleep(sleep_time)
                            continue
                        else:
                            failures_summary.append(f"{provider_name}: {err_msg}")
                            next_p = chain[provider_idx + 1] if provider_idx + 1 < len(chain) else None
                            next_provider_name = (
                                getattr(next_p, "name", getattr(next_p, "provider_name", next_p.__class__.__name__.replace("AgentProvider", "").lower()))
                                if next_p
                                else "NONE"
                            )
                            task.record_trace(
                                step=task.step_count,
                                action="provider_fallback",
                                result={
                                    "failed_provider": provider_name,
                                    "next_provider": next_provider_name,
                                    "reason": err_msg,
                                },
                            )
                            break  # Fallback to next provider

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
                    if self._is_fatal_error(err_str):
                        logger.error(f"Fatal exception on provider '{provider_name}': {err_str}")
                        return AgentDecision(
                            type=AgentDecisionType.FAIL,
                            error_message=f"Fatal error on provider {provider_name}: {err_str}",
                        )

                    if attempt < self.max_retries_per_provider:
                        sleep_time = min((attempt + 1) * 2.0, self.max_backoff_seconds)
                        logger.warning(f"Exception on provider '{provider_name}' ({err_str}). Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        failures_summary.append(f"{provider_name}: {err_str}")
                        next_p = chain[provider_idx + 1] if provider_idx + 1 < len(chain) else None
                        next_provider_name = (
                            getattr(next_p, "name", getattr(next_p, "provider_name", next_p.__class__.__name__.replace("AgentProvider", "").lower()))
                            if next_p
                            else "NONE"
                        )
                        task.record_trace(
                            step=task.step_count,
                            action="provider_fallback",
                            result={
                                "failed_provider": provider_name,
                                "next_provider": next_provider_name,
                                "reason": err_str,
                            },
                        )
                        break

        # If all providers failed
        all_err = " All LLM providers in fallback chain failed: " + "; ".join(failures_summary)
        logger.error(all_err)
        return AgentDecision(
            type=AgentDecisionType.FAIL,
            error_message=all_err,
        )
