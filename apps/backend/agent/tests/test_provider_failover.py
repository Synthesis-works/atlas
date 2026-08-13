import pytest
from unittest.mock import MagicMock

from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.gemini import GeminiAgentProvider
from apps.backend.agent.providers.grok import GrokAgentProvider
from apps.backend.agent.providers.mistral import MistralAgentProvider
from apps.backend.agent.providers.mock import MockAgentProvider
from apps.backend.agent.providers.router import ProviderRouter
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask, AgentTaskStatus


class FailingProvider(BaseLLMProvider):
    """Test helper provider that simulates specific transient or fatal errors."""
    def __init__(self, name: str, error_message: str):
        self.name = name
        self.error_message = error_message

    def decide(self, task: AgentTask, prompt_context: str, available_tools: list) -> AgentDecision:
        return AgentDecision(
            type=AgentDecisionType.FAIL,
            error_message=self.error_message,
        )


class SuccessfulProvider(BaseLLMProvider):
    """Test helper provider that simulates successful tool calls or final responses."""
    def __init__(self, name: str, decision: AgentDecision):
        self.name = name
        self.decision = decision

    def decide(self, task: AgentTask, prompt_context: str, available_tools: list) -> AgentDecision:
        return self.decision


def test_gemini_success_no_fallback():
    gemini = SuccessfulProvider("gemini", AgentDecision(type=AgentDecisionType.FINAL_RESPONSE, response="Done by Gemini"))
    grok = SuccessfulProvider("grok", AgentDecision(type=AgentDecisionType.FINAL_RESPONSE, response="Done by Grok"))
    router = ProviderRouter(primary=gemini, fallbacks=[grok], max_retries_per_provider=0)

    task = AgentTask(goal="Test primary success")
    decision = router.decide(task, "prompt", [])

    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Done by Gemini"
    assert task.current_provider == "gemini"


def test_gemini_429_failover_to_grok():
    gemini_429 = FailingProvider("gemini", "Gemini API error: 429 RESOURCE_EXHAUSTED Quota exceeded")
    grok_success = SuccessfulProvider(
        "grok",
        AgentDecision(type=AgentDecisionType.TOOL_CALL, tool_name="create_benchmark", arguments={"name": "Test BM"}),
    )

    router = ProviderRouter(primary=gemini_429, fallbacks=[grok_success], max_retries_per_provider=0)
    task = AgentTask(goal="Test 429 failover")

    decision = router.decide(task, "prompt", [])

    assert decision.type == AgentDecisionType.TOOL_CALL
    assert decision.tool_name == "create_benchmark"
    assert task.current_provider == "grok"

    # Verify telemetry trace recorded fallback
    trace_events = [t for t in task.execution_trace if t.event_type == "provider_fallback"]
    assert len(trace_events) == 1
    assert trace_events[0].details["failed_provider"] == "gemini"
    assert trace_events[0].details["next_provider"] == "grok"


def test_gemini_503_timeout_failover_to_mistral():
    gemini_503 = FailingProvider("gemini", "Gemini API error: 503 Service Unavailable")
    grok_timeout = FailingProvider("grok", "Grok connection timeout")
    mistral_success = SuccessfulProvider(
        "mistral",
        AgentDecision(type=AgentDecisionType.FINAL_RESPONSE, response="Mistral finished task"),
    )

    router = ProviderRouter(primary=gemini_503, fallbacks=[grok_timeout, mistral_success], max_retries_per_provider=0)
    task = AgentTask(goal="Test multi-fallback")

    decision = router.decide(task, "prompt", [])

    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Mistral finished task"
    assert task.current_provider == "mistral"


def test_all_providers_failing():
    gemini_fail = FailingProvider("gemini", "Gemini 500 error")
    grok_fail = FailingProvider("grok", "Grok 502 error")
    mistral_fail = FailingProvider("mistral", "Mistral 503 error")

    router = ProviderRouter(primary=gemini_fail, fallbacks=[grok_fail, mistral_fail], max_retries_per_provider=0)
    task = AgentTask(goal="Test all failing")

    decision = router.decide(task, "prompt", [])

    assert decision.type == AgentDecisionType.FAIL
    assert "All LLM providers in fallback chain failed" in decision.error_message


def test_fatal_error_no_inappropriate_fallback():
    gemini_401 = FailingProvider("gemini", "401 Unauthorized: Invalid API Key")
    grok_success = SuccessfulProvider("grok", AgentDecision(type=AgentDecisionType.FINAL_RESPONSE, response="Grok"))

    router = ProviderRouter(primary=gemini_401, fallbacks=[grok_success], max_retries_per_provider=0)
    task = AgentTask(goal="Test fatal 401 fast-fail")

    decision = router.decide(task, "prompt", [])

    assert decision.type == AgentDecisionType.FAIL
    assert "401" in decision.error_message
    # Verify Grok was NOT called (current_provider remains gemini)
    assert task.current_provider == "gemini"


def test_context_preservation_on_fallback():
    captured_contexts = []

    class CapturingProvider(BaseLLMProvider):
        def __init__(self, name: str):
            self.name = name
        def decide(self, task: AgentTask, prompt_context: str, available_tools: list) -> AgentDecision:
            captured_contexts.append((self.name, prompt_context))
            if self.name == "gemini":
                return AgentDecision(type=AgentDecisionType.FAIL, error_message="429 Rate Limit")
            return AgentDecision(type=AgentDecisionType.FINAL_RESPONSE, response="Fallback completed")

    router = ProviderRouter(
        primary=CapturingProvider("gemini"),
        fallbacks=[CapturingProvider("grok")],
        max_retries_per_provider=0,
    )

    task = AgentTask(goal="Test context preservation")
    context_str = "GOAL: Create benchmark\nPLAN: 1. Create 2. Validate\nOBSERVATIONS: Step 1 success"
    
    decision = router.decide(task, context_str, [])

    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert len(captured_contexts) == 2
    assert captured_contexts[0][1] == context_str
    assert captured_contexts[1][1] == context_str  # Context preserved 100% for Grok!


def test_tool_call_normalization():
    grok_provider = GrokAgentProvider()
    mistral_provider = MistralAgentProvider()

    # Test normalization of JSON string content into AgentDecision
    mock_grok_resp = MagicMock()
    mock_grok_resp.response = '{"tool_name": "create_dataset", "arguments": {"name": "test_ds"}}'
    grok_provider.client.generate = MagicMock(return_value=mock_grok_resp)

    task = AgentTask(goal="Normalize tool calls")
    decision = grok_provider.decide(task, "prompt", [])

    assert decision.type == AgentDecisionType.TOOL_CALL
    assert decision.tool_name == "create_dataset"
    assert decision.arguments == {"name": "test_ds"}
