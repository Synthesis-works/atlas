"""
Provider integration contract tests (Requirement G).

Covers:
- Each production provider (Gemini, Groq, Mistral) produces valid decisions.
- Gemini schema is sent unchanged (native functionDeclarations, UPPERCASE types).
- Groq/Mistral receive OpenAI-compatible normalized schemas (lowercase types),
  including recursive normalization of nested objects / items / additionalProperties.
- Router ordering: Gemini -> Groq -> Mistral (Grok excluded from production chain).
- Fallback behavior: Gemini fail -> Groq attempted; Gemini+Groq fail -> Mistral attempted.
- All-fail path preserves provider chain info in the error.

All external API calls are mocked — no network access and no Gemini quota burn.
"""

import json

import pytest
from packages.llm.models.response import LLMResponse

from apps.backend.agent.providers.gemini import GeminiAgentProvider
from apps.backend.agent.providers.groq import GroqAgentProvider
from apps.backend.agent.providers.mistral import MistralAgentProvider
from apps.backend.agent.providers.router import (
    PROVIDER_REGISTRY,
    ProviderRouter,
    build_provider_instance,
    get_configured_providers,
)
from apps.backend.agent.providers.schema_utils import (
    normalize_tool_schema_for_openai,
    normalize_tools_for_openai,
)
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask


def make_raw(provider: str, content: str = "", tool_calls: list | None = None) -> dict:
    """Build a fake provider response payload.

    OpenAI-compatible providers (Groq/Mistral) use ``choices``;
    Gemini uses ``candidates`` with content parts.
    """
    if provider == "gemini":
        parts: list[dict] = []
        if tool_calls:
            fn = tool_calls[0]["function"]
            parts.append(
                {
                    "functionCall": {
                        "name": fn["name"],
                        "args": json.loads(fn["arguments"])
                        if isinstance(fn["arguments"], str)
                        else fn.get("arguments", {}),
                    }
                }
            )
        if content:
            parts.append({"text": content})
        return {"candidates": [{"content": {"parts": parts}}], "usageMetadata": {}}
    message: dict = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}], "usage": {}}


class FakeClient:
    """Droppable stand-in for any provider client. Records last request."""

    def __init__(self, response_payload: dict, api_key: str = "test-key"):
        self.response_payload = response_payload
        self.api_key = api_key
        self.last_kwargs: dict = {}

    def health(self) -> bool:
        return bool(self.api_key)

    def generate(self, model: str, prompt, **kwargs) -> LLMResponse:
        self.last_kwargs = {"model": model, "prompt": prompt, **kwargs}
        return LLMResponse(
            provider="fake",
            model=model,
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            latency_ms=5,
            response=kwargs.get("response", ""),
            raw=self.response_payload,
            created_at="0",
        )


@pytest.fixture
def task() -> AgentTask:
    return AgentTask(goal="Create Math Benchmark")


def sample_gemini_tools() -> list[dict]:
    """A small Gemini-style functionDeclaration list with nested UPPERCASE types."""
    return [
        {
            "name": "create_dataset",
            "description": "Create a dataset",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "benchmark_id": {"type": "STRING", "description": "Benchmark UUID"},
                    "name": {"type": "STRING"},
                    "metadata": {
                        "type": "OBJECT",
                        "properties": {
                            "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
                            "score": {"type": "NUMBER"},
                        },
                        "additionalProperties": {"type": "STRING"},
                    },
                    "config": {
                        "type": "OBJECT",
                        "properties": {"mode": {"type": "STRING"}},
                        "anyOf": [{"type": "OBJECT", "properties": {"a": {"type": "INTEGER"}}}],
                        "oneOf": [{"type": "OBJECT", "properties": {"b": {"type": "BOOLEAN"}}}],
                    },
                },
                "required": ["benchmark_id", "name"],
            },
        }
    ]


# ---------------------------------------------------------------------------
# Provider decision contracts
# ---------------------------------------------------------------------------


def test_gemini_provider_tool_call_decision():
    raw = make_raw(
        "gemini",
        tool_calls=[
            {
                "function": {
                    "name": "create_benchmark",
                    "arguments": json.dumps({"name": "Math Benchmark"}),
                }
            }
        ],
    )
    provider = GeminiAgentProvider(client=FakeClient(raw))
    decision = provider.decide(task, "ctx", sample_gemini_tools())
    assert isinstance(decision, AgentDecision)
    assert decision.type == AgentDecisionType.TOOL_CALL
    assert decision.tool_name == "create_benchmark"
    assert decision.arguments == {"name": "Math Benchmark"}


def test_gemini_provider_final_response_decision():
    raw = make_raw("gemini", content="All steps completed.")
    provider = GeminiAgentProvider(client=FakeClient(raw))
    decision = provider.decide(task, "ctx", sample_gemini_tools())
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "All steps completed."


def test_groq_provider_tool_call_decision():
    raw = make_raw(
        "groq",
        tool_calls=[
            {
                "function": {
                    "name": "create_dataset",
                    "arguments": json.dumps({"name": "D1", "benchmark_id": "bm-1"}),
                }
            }
        ],
    )
    provider = GroqAgentProvider(client=FakeClient(raw))
    decision = provider.decide(task, "ctx", sample_gemini_tools())
    assert decision.type == AgentDecisionType.TOOL_CALL
    assert decision.tool_name == "create_dataset"
    assert decision.arguments == {"name": "D1", "benchmark_id": "bm-1"}


def test_mistral_provider_tool_call_decision():
    raw = make_raw(
        "mistral",
        tool_calls=[
            {
                "function": {
                    "name": "create_dataset",
                    "arguments": json.dumps({"name": "D1", "benchmark_id": "bm-1"}),
                }
            }
        ],
    )
    provider = MistralAgentProvider(client=FakeClient(raw))
    decision = provider.decide(task, "ctx", sample_gemini_tools())
    assert decision.type == AgentDecisionType.TOOL_CALL
    assert decision.tool_name == "create_dataset"


def test_mistral_provider_json_text_fallback():
    raw = make_raw(
        "mistral", content='{"tool_name": "create_benchmark", "arguments": {"name": "X"}}'
    )
    provider = MistralAgentProvider(client=FakeClient(raw))
    decision = provider.decide(task, "ctx", sample_gemini_tools())
    assert decision.type == AgentDecisionType.TOOL_CALL
    assert decision.tool_name == "create_benchmark"


# ---------------------------------------------------------------------------
# Schema normalization contracts (Requirement C)
# ---------------------------------------------------------------------------


def test_gemini_schema_unchanged_native_uppercase():
    """Gemini must receive the original UPPERCASE functionDeclarations untouched."""
    tools = sample_gemini_tools()
    raw = make_raw("gemini", content="done")
    client = FakeClient(raw)
    provider = GeminiAgentProvider(client=client)
    provider.decide(task, "ctx", tools)

    sent_tools = client.last_kwargs.get("tools")
    assert sent_tools is not None
    assert sent_tools == [{"functionDeclarations": tools}]
    assert sent_tools[0]["functionDeclarations"][0]["parameters"]["type"] == "OBJECT"


def test_normalize_openai_lowercase_top_level():
    normalized = normalize_tool_schema_for_openai(sample_gemini_tools()[0])
    params = normalized["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"]["benchmark_id"]["type"] == "string"
    assert params["properties"]["name"]["type"] == "string"


def test_normalize_recursive_nested_objects_and_additional_properties():
    normalized = normalize_tool_schema_for_openai(sample_gemini_tools()[0])
    metadata = normalized["function"]["parameters"]["properties"]["metadata"]
    assert metadata["type"] == "object"
    assert metadata["properties"]["tags"]["type"] == "array"
    assert metadata["properties"]["tags"]["items"]["type"] == "string"
    assert metadata["properties"]["score"]["type"] == "number"
    # Requirement C: additionalProperties must be recursed.
    assert metadata["additionalProperties"]["type"] == "string"


def test_normalize_anyof_oneof_recursion():
    normalized = normalize_tool_schema_for_openai(sample_gemini_tools()[0])
    config = normalized["function"]["parameters"]["properties"]["config"]
    assert config["anyOf"][0]["type"] == "object"
    assert config["anyOf"][0]["properties"]["a"]["type"] == "integer"
    assert config["oneOf"][0]["type"] == "object"
    assert config["oneOf"][0]["properties"]["b"]["type"] == "boolean"


def test_normalize_does_not_mutate_original_gemini_schema():
    original = sample_gemini_tools()
    normalize_tools_for_openai(original)
    params = original[0]["parameters"]
    assert params["type"] == "OBJECT"
    assert params["properties"]["metadata"]["type"] == "OBJECT"
    assert params["properties"]["metadata"]["properties"]["tags"]["type"] == "ARRAY"
    assert params["properties"]["config"]["anyOf"][0]["type"] == "OBJECT"


def test_normalize_array_items_and_number():
    tools = [
        {
            "name": "run_benchmark",
            "description": "run",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "scores": {"type": "ARRAY", "items": {"type": "NUMBER"}},
                },
            },
        }
    ]
    normalized = normalize_tool_schema_for_openai(tools[0])
    scores = normalized["function"]["parameters"]["properties"]["scores"]
    assert scores["type"] == "array"
    assert scores["items"]["type"] == "number"


def test_groq_receives_normalized_lowercase_schema():
    raw = make_raw("groq", content="ok")
    client = FakeClient(raw)
    provider = GroqAgentProvider(client=client)
    provider.decide(task, "ctx", sample_gemini_tools())

    sent_tools = client.last_kwargs.get("tools")
    assert sent_tools is not None
    assert sent_tools[0]["type"] == "function"
    assert sent_tools[0]["function"]["parameters"]["type"] == "object"
    assert sent_tools[0]["function"]["parameters"]["properties"]["name"]["type"] == "string"


def test_mistral_receives_normalized_lowercase_schema():
    raw = make_raw("mistral", content="ok")
    client = FakeClient(raw)
    provider = MistralAgentProvider(client=client)
    provider.decide(task, "ctx", sample_gemini_tools())

    sent_tools = client.last_kwargs.get("tools")
    assert sent_tools is not None
    assert sent_tools[0]["type"] == "function"
    assert sent_tools[0]["function"]["parameters"]["type"] == "object"
    assert sent_tools[0]["function"]["parameters"]["properties"]["name"]["type"] == "string"


# ---------------------------------------------------------------------------
# Registry & Router ordering (Requirements B, D)
# ---------------------------------------------------------------------------


def test_provider_registry_excludes_grok(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setenv("MISTRAL_API_KEY", "test")
    values = [p.value for p in get_configured_providers(include_test_only=False)]
    assert "grok" not in values
    assert "mock" not in values
    assert "gemini" in values
    assert "groq" in values
    assert "mistral" in values


def test_build_provider_instance_unknown_returns_none():
    assert build_provider_instance("nonsense") is None


def test_router_default_ordering_gemini_groq_mistral(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setenv("MISTRAL_API_KEY", "test")
    router = ProviderRouter(max_retries_per_provider=0, max_backoff_seconds=0.1)
    assert router.primary.__class__ is GeminiAgentProvider
    assert router.fallbacks[0].__class__ is GroqAgentProvider
    assert router.fallbacks[1].__class__ is MistralAgentProvider


def test_router_primary_override_excludes_duplicate(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setenv("MISTRAL_API_KEY", "test")
    gemini = GeminiAgentProvider(client=FakeClient(make_raw("gemini", content="ok")))
    router = ProviderRouter(primary=gemini, max_retries_per_provider=0, max_backoff_seconds=0.1)
    # The explicitly-provided primary must NOT be duplicated in the auto fallbacks.
    assert all(p.__class__ is not GeminiAgentProvider for p in router.fallbacks)
    assert len(router.fallbacks) == 2


def test_router_gemini_fails_groq_attempted():
    from apps.backend.agent.tests.test_provider_failover import MockProviderScenario

    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 Rate limit"}]
    )
    groq = MockProviderScenario(
        "groq",
        [
            {
                "type": AgentDecisionType.TOOL_CALL,
                "tool_name": "create_benchmark",
                "arguments": {"name": "M"},
            }
        ],
    )
    router = ProviderRouter(primary=gemini, fallbacks=[groq], max_retries_per_provider=0)
    task = AgentTask(goal="Test", granted_permissions=[])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.TOOL_CALL
    assert task.current_provider == "groq"
    assert groq.call_count == 1


def test_router_gemini_and_groq_fail_mistral_success():
    from apps.backend.agent.tests.test_provider_failover import MockProviderScenario

    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 Rate limit"}]
    )
    groq = MockProviderScenario(
        "groq", [{"type": AgentDecisionType.FAIL, "error": "400 Model not found"}]
    )
    mistral = MockProviderScenario(
        "mistral", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Mistral OK"}]
    )
    router = ProviderRouter(primary=gemini, fallbacks=[groq, mistral], max_retries_per_provider=0)
    task = AgentTask(goal="Test", granted_permissions=[])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Mistral OK"
    assert task.current_provider == "mistral"
    assert mistral.call_count == 1


def test_router_all_providers_fail_preserves_chain_info():
    from apps.backend.agent.tests.test_provider_failover import MockProviderScenario

    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 Rate limit"}]
    )
    groq = MockProviderScenario(
        "groq", [{"type": AgentDecisionType.FAIL, "error": "400 Model not found"}]
    )
    mistral = MockProviderScenario(
        "mistral", [{"type": AgentDecisionType.FAIL, "error": "503 upstream"}]
    )
    router = ProviderRouter(primary=gemini, fallbacks=[groq, mistral], max_retries_per_provider=0)
    task = AgentTask(goal="Test", granted_permissions=[])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FAIL
    assert "gemini" in decision.error_message
    assert "groq" in decision.error_message
    assert "mistral" in decision.error_message
