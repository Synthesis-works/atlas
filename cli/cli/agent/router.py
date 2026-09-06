"""Client-side agent LLM provider router (v3.1).

``ProviderRouter`` presents the same ``LLMProvider`` surface the loop already
consumes (``available()`` + ``decide(...)``), but internally holds an ordered
list of concrete providers and falls back across them for *genuine availability*
failures only.

Fallback semantics
    A provider is skipped before a call when it is not ``available()`` (no key
    configured).  During a call a provider may raise
    ``AgentProviderUnavailableError`` (network/DNS, timeout, 429, 5xx, or the
    configured provider simply missing); the router then tries the next
    available provider.  A ``FAIL`` decision is returned immediately - it
    signals a non-availability problem (invalid key, invalid request, malformed
    output) that must not be masked by bouncing providers.

    ``allow_fallback=False`` (an explicit ``--provider`` choice) disables the
    cross-provider bounce: only the named provider runs.

User-facing messages
    The router returns a *friendly* ``error_message`` for provider-failure
    cases (e.g. "The AI provider is temporarily unavailable. Please try again
    in a moment.").  The raw technical detail is stored in the ``detail`` field
    of the ``AgentDecision`` so that callers can surface it in verbose/debug
    mode without cluttering the default interactive experience.
"""

from __future__ import annotations

from typing import Any

from cli.agent.provider import (
    AgentProviderUnavailableError,
    LLMProvider,
)
from cli.agent.state import AgentDecision, AgentDecisionType


class ProviderRouter(LLMProvider):
    name = "auto"

    def __init__(
        self,
        providers: list[LLMProvider],
        *,
        default_provider: str | None = None,
        allow_fallback: bool = True,
    ) -> None:
        """:param providers: tried in order (first available wins by default).
        :param default_provider: optional id to pin to; None/blank means iterate.
        :param allow_fallback: False disables cross-provider fallback (pin).
        """
        self.providers = providers
        self.default_provider = default_provider
        self.allow_fallback = allow_fallback

    @property
    def ordered(self) -> list[LLMProvider]:
        """Providers in call order honouring ``default_provider`` pin."""
        if not self.default_provider:
            return list(self.providers)
        pinned = next((p for p in self.providers if p.name == self.default_provider), None)
        if pinned is None:
            return list(self.providers)
        return [pinned] + [p for p in self.providers if p.name != pinned.name]

    @property
    def available(self) -> bool:
        return any(p.available for p in self.providers)

    def available_provider_ids(self) -> list[str]:
        return [p.name for p in self.providers if p.available]

    def decide(
        self,
        task: str,
        prompt_context: str,
        available_tools: list[dict[str, Any]],
    ) -> AgentDecision:
        available = [p for p in self.ordered if p.available]

        if not available:
            names = [p.name for p in self.ordered]
            available_names = self.available_provider_ids()
            avail_str = ", ".join(available_names) if available_names else "none"
            detail = (
                f"No provider available. Configured: {', '.join(names)}; "
                f"available: {avail_str}. Set GROQ_API_KEY or GEMINI_API_KEY."
            )
            return AgentDecision(
                type=AgentDecisionType.FAIL,
                error_message=(
                    "No AI provider is configured. "
                    "Set GROQ_API_KEY or GEMINI_API_KEY to use the agent."
                ),
                detail=detail,
            )

        # Explicit --provider: pin to the named provider; no fallback.
        if not self.allow_fallback and self.default_provider:
            pinned = next((p for p in available if p.name == self.default_provider), None)
            if pinned is None:
                avail_str = ", ".join(p.name for p in available)
                return AgentDecision(
                    type=AgentDecisionType.FAIL,
                    error_message=(
                        f"Provider '{self.default_provider}' is not available "
                        f"(available: {avail_str})."
                    ),
                )
            try:
                return pinned.decide(task, prompt_context, available_tools)
            except AgentProviderUnavailableError as exc:
                raw = f"{pinned.name}: {exc}"
                return AgentDecision(
                    type=AgentDecisionType.FAIL,
                    error_message=(
                        f"Provider '{pinned.name}' is temporarily unavailable. "
                        "Please try again in a moment."
                    ),
                    detail=raw,
                )

        # Auto / fallback mode: try each available provider in order.
        last_raw: str | None = None
        for provider in available:
            try:
                decision = provider.decide(task, prompt_context, available_tools)
            except AgentProviderUnavailableError as exc:
                last_raw = f"{provider.name}: {exc}"
                continue
            except Exception as exc:  # noqa: BLE001
                # Unexpected provider bug: NOT an availability failure.  Return a
                # FAIL decision instead of bouncing to another provider.
                return AgentDecision(
                    type=AgentDecisionType.FAIL,
                    error_message=(
                        "The AI provider returned an unexpected error. "
                        "Please try again in a moment."
                    ),
                    detail=f"agent provider decision failed: {exc}",
                )
            return decision

        return AgentDecision(
            type=AgentDecisionType.FAIL,
            error_message=(
                "The AI provider is temporarily unavailable. Please try again in a moment."
            ),
            detail=f"All providers failed: {last_raw or 'unknown error'}",
        )
