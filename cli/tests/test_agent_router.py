"""Tests for the v3.1 ``ProviderRouter`` fallback behaviour.

Covers: default order, the availability classifier (GenAi availability vs
non-availability errors), fallback on genuine availability failures, no-fallback
when pinned via ``--provider``, immediate FAIL on non-availability errors, and
the all-providers-unavailable path.
"""

from __future__ import annotations

from typing import Any

from cli.agent.provider import (
    AgentProviderUnavailableError,
    LLMProvider,
)
from cli.agent.router import ProviderRouter
from cli.agent.state import AgentDecision, AgentDecisionType


class _Stub(LLMProvider):
    """Deterministic provider stub for router tests."""

    def __init__(
        self,
        *,
        name: str,
        available: bool = True,
        result: AgentDecision | None = None,
        raise_on_decide: Exception | None = None,
    ) -> None:
        self.name = name
        self._avail = available
        self._result = result
        self._raise = raise_on_decide
        self.calls = 0

    @property
    def available(self) -> bool:
        return self._avail

    def decide(
        self, task: str, prompt_context: str, available_tools: list[dict[str, Any]]
    ) -> AgentDecision:
        self.calls += 1
        if self._raise is not None:
            raise self._raise
        return self._result or AgentDecision(
            type=AgentDecisionType.FINAL_RESPONSE,
            response=f"answered by {self.name}",
        )


def _final(response: str) -> AgentDecision:
    return AgentDecision(type=AgentDecisionType.FINAL_RESPONSE, response=response)


class TestAvailabilityClassifier:
    def test_network_dns_is_availability(self) -> None:
        from cli.agent.provider import is_availability_failure

        assert is_availability_failure("Request failed: [Errno 11001] getaddrinfo failed")
        assert is_availability_failure("connect() raised ConnectionRefusedError")

    def test_timeout_is_availability(self) -> None:
        from cli.agent.provider import is_availability_failure

        assert is_availability_failure("The read operation timed out")

    def test_rate_limit_is_availability(self) -> None:
        from cli.agent.provider import is_availability_failure

        assert is_availability_failure("Groq API error (429): Rate limit exceeded")

    def test_server_error_is_availability(self) -> None:
        from cli.agent.provider import is_availability_failure

        assert is_availability_failure("provider returned 503 Service Unavailable")

    def test_invalid_api_key_is_not_availability(self) -> None:
        from cli.agent.provider import is_availability_failure

        assert not is_availability_failure("Groq API error (401): Invalid API key")
        assert not is_availability_failure("API key not found for Gemini.")

    def test_invalid_request_is_not_availability(self) -> None:
        from cli.agent.provider import is_availability_failure

        assert not is_availability_failure("Invalid request: bad tool call format")


class TestRouterFallback:
    def test_falls_back_on_unavailable_error(self) -> None:
        groq = _Stub(name="groq", raise_on_decide=AgentProviderUnavailableError("down"))
        gemini = _Stub(name="gemini", result=_final("gemini got it"))
        router = ProviderRouter(providers=[groq, gemini])
        decision = router.decide("t", "c", [])
        assert decision.type is AgentDecisionType.FINAL_RESPONSE
        assert decision.response == "gemini got it"
        assert groq.calls == 1
        assert gemini.calls == 1

    def test_uses_first_available_when_no_failure(self) -> None:
        groq = _Stub(name="groq", result=_final("groq got it"))
        gemini = _Stub(name="gemini")
        router = ProviderRouter(providers=[groq, gemini])
        decision = router.decide("t", "c", [])
        assert decision.response == "groq got it"
        assert gemini.calls == 0

    def test_bounces_in_availability_error(self) -> None:
        raise_on = AgentProviderUnavailableError("server 500")
        groq = _Stub(name="groq", raise_on_decide=raise_on)
        gemini = _Stub(name="gemini", raise_on_decide=raise_on)
        router = ProviderRouter(providers=[groq, gemini])
        decision = router.decide("t", "c", [])
        assert decision.type is AgentDecisionType.FAIL
        assert "temporarily unavailable" in decision.error_message
        assert decision.detail and "providers failed" in decision.detail
        assert groq.calls == 1
        assert gemini.calls == 1

    def test_skips_unavailable_providers_picks_healthy(self) -> None:
        groq = _Stub(name="groq", available=False)
        gemini = _Stub(name="gemini", result=_final("only gemini"))
        router = ProviderRouter(providers=[groq, gemini])
        decision = router.decide("t", "c", [])
        assert decision.response == "only gemini"
        assert groq.calls == 0

    def test_no_candidates_returns_fail(self) -> None:
        router = ProviderRouter(
            providers=[_Stub(name="groq", available=False), _Stub(name="gemini", available=False)]
        )
        decision = router.decide("t", "c", [])
        assert decision.type is AgentDecisionType.FAIL
        assert "No AI provider is configured" in decision.error_message

    def test_non_availability_error_returns_fail_immediately(self) -> None:
        groq = _Stub(name="groq", raise_on_decide=ValueError("Invalid API key"))
        gemini = _Stub(name="gemini", result=_final("should-not-run"))
        router = ProviderRouter(providers=[groq, gemini])
        decision = router.decide("t", "c", [])
        assert decision.type is AgentDecisionType.FAIL
        assert "unexpected error" in decision.error_message
        assert decision.detail and "Invalid API key" in decision.detail
        assert gemini.calls == 0


class TestRouterPin:
    def test_pinned_provider_runs_only_that_provider(self) -> None:
        groq = _Stub(name="groq", raise_on_decide=AgentProviderUnavailableError("429"))
        gemini = _Stub(name="gemini", result=_final("would-handle"))
        router = ProviderRouter(
            providers=[groq, gemini], default_provider="groq", allow_fallback=False
        )
        decision = router.decide("t", "c", [])
        assert decision.type is AgentDecisionType.FAIL
        assert "unavailable" in decision.error_message
        assert gemini.calls == 0

    def test_pinned_unavailable_provider_returns_fail(self) -> None:
        groq = _Stub(name="groq", available=False)
        gemini = _Stub(name="gemini", available=True, result=_final("x"))
        router = ProviderRouter(
            providers=[groq, gemini], default_provider="groq", allow_fallback=False
        )
        decision = router.decide("t", "c", [])
        assert decision.type is AgentDecisionType.FAIL
        assert "not available" in decision.error_message
        assert gemini.calls == 0

    def test_pinned_success(self) -> None:
        groq = _Stub(name="groq", result=_final("groq pinned"))
        gemini = _Stub(name="gemini")
        router = ProviderRouter(
            providers=[gemini, groq], default_provider="groq", allow_fallback=False
        )
        decision = router.decide("t", "c", [])
        assert decision.response == "groq pinned"
        assert gemini.calls == 0


class TestRouterOrdering:
    def test_default_provider_ordering_put_first(self) -> None:
        groq = _Stub(name="groq", result=_final("g"))
        gemini = _Stub(name="gemini", result=_final("m"))
        router = ProviderRouter(providers=[gemini, groq], default_provider="groq")
        assert router.ordered[0].name == "groq"

    def test_unknown_pin_keeps_original_order(self) -> None:
        groq = _Stub(name="groq", result=_final("g"))
        gemini = _Stub(name="gemini", result=_final("m"))
        router = ProviderRouter(providers=[gemini, groq], default_provider="nope")
        assert [p.name for p in router.ordered] == ["gemini", "groq"]
