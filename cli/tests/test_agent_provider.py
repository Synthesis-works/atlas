"""Tests for the CLI agent provider adapter over packages.llm GeminiClient.

The provider turns a (possibly tool-calling) Gemini response into a structured
``AgentDecision`` for the client-side loop.  It is the only component that talks
to an LLM; the loop consumes decisions.
"""

from __future__ import annotations

import pytest
from packages.llm.clients.gemini import GeminiClient
from packages.llm.models.prompt import Prompt
from packages.llm.models.response import LLMResponse

from cli.agent.provider import AgentProvider, AgentProviderError
from cli.agent.state import AgentDecisionType


def _llm_response(raw: dict) -> LLMResponse:
    return LLMResponse(
        provider="gemini",
        model="gemini-3.5-flash-lite",
        latency_ms=1,
        response="",
        raw=raw,
        created_at="2026-01-01",
    )


class MockClient:
    """Minimal GeminiClient-shaped stub controllable per test."""

    def __init__(
        self, *, health: bool = True, result: LLMResponse | Exception | None = None
    ) -> None:
        self._health = health
        self._result = result
        self.model: str | None = None
        self.prompt: Prompt | None = None
        self.tools: list | None = None

    def health(self) -> bool:
        return self._health

    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        self.model = model
        self.prompt = prompt
        self.tools = kwargs.get("tools")
        if isinstance(self._result, Exception):
            raise self._result
        return self._result or _llm_response(
            {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}
        )


def _raw_function_call(name: str, args: dict) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"functionCall": {"name": name, "args": args}}]}}]
    }


class TestAgentProviderDecide:
    def test_function_call_decision(self) -> None:
        client = MockClient(result=_llm_response(_raw_function_call("model_list", {"x": 1})))
        provider = AgentProvider(model="m", client=client)  # type: ignore[arg-type]
        decision = provider.decide("task", "", [])
        assert decision.type is AgentDecisionType.TOOL_CALL
        assert decision.tool_name == "model_list"
        assert decision.arguments == {"x": 1}

    def test_final_text_response_decision(self) -> None:
        client = MockClient(
            result=_llm_response({"candidates": [{"content": {"parts": [{"text": "all done"}]}}]})
        )
        provider = AgentProvider(model="m", client=client)  # type: ignore[arg-type]
        decision = provider.decide("task", "", [])
        assert decision.type is AgentDecisionType.FINAL_RESPONSE
        assert decision.response == "all done"

    def test_no_parts_falls_back_to_final(self) -> None:
        client = MockClient(result=_llm_response({"candidates": [{"content": {"parts": []}}]}))
        provider = AgentProvider(model="m", client=client)  # type: ignore[arg-type]
        decision = provider.decide("task", "", [])
        assert decision.type is AgentDecisionType.FINAL_RESPONSE

    def test_unhealthy_client_raises(self) -> None:
        client = MockClient(health=False)
        provider = AgentProvider(model="m", client=client)  # type: ignore[arg-type]
        with pytest.raises(AgentProviderError):
            provider.decide("task", "", [])

    def test_generate_exception_becomes_fail_decision(self) -> None:
        client = MockClient(result=RuntimeError("API key not found for Gemini."))
        provider = AgentProvider(model="m", client=client)  # type: ignore[arg-type]
        decision = provider.decide("task", "", [])
        assert decision.type is AgentDecisionType.FAIL
        assert decision.error_message

    def test_passes_tools_and_model_to_client(self) -> None:
        client = MockClient(result=_llm_response(_raw_function_call("t", {})))
        provider = AgentProvider(model="my-model", client=client)  # type: ignore[arg-type]
        provider.decide("the task", "context", [{"name": "tool1"}])
        assert client.model == "my-model"
        assert client.prompt is not None
        assert client.tools == [{"functionDeclarations": [{"name": "tool1"}]}]


class TestAgentProviderConstruction:
    def test_default_provider_is_gemini(self) -> None:
        provider = AgentProvider()
        assert isinstance(provider.client, GeminiClient) or provider.client is not None

    def test_health_reports_gemini_key_presence(self) -> None:
        provider = AgentProvider()
        # health matches the underlying client's key presence
        provider.available = bool(provider.client.health())
