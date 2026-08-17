import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.router import ProviderRouter
from apps.backend.agent.state import (
    AgentDecision,
    AgentDecisionType,
    AgentPermission,
    AgentTask,
    AgentTaskStatus,
)
from apps.backend.agent.tools.registry import ToolRegistry


class MockProviderScenario(BaseLLMProvider):
    def __init__(self, name: str, responses: list[dict]):
        self.name = name
        self.responses = list(responses)
        self.call_count = 0

    def decide(self, task: AgentTask, prompt_context: str, available_tools: list) -> AgentDecision:
        self.call_count += 1
        if not self.responses:
            return AgentDecision(
                type=AgentDecisionType.FAIL, error_message=f"{self.name} out of responses"
            )

        curr = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        dtype = curr.get("type", AgentDecisionType.FAIL)

        if dtype == AgentDecisionType.FAIL:
            return AgentDecision(type=dtype, error_message=curr.get("error", "Error"))
        elif dtype == AgentDecisionType.TOOL_CALL:
            return AgentDecision(
                type=dtype, tool_name=curr.get("tool_name"), arguments=curr.get("arguments", {})
            )
        else:
            return AgentDecision(type=dtype, response=curr.get("response", "Done"))


def test_scenario_a_gemini_success():
    primary = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Gemini Ok"}]
    )
    router = ProviderRouter(primary=primary)
    task = AgentTask(goal="Test A", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Gemini Ok"
    assert task.current_provider == "gemini"


def test_scenario_b_gemini_429_retry_success():
    primary = MockProviderScenario(
        "gemini",
        [
            {"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"},
            {"type": AgentDecisionType.FINAL_RESPONSE, "response": "Gemini Retry Success"},
        ],
    )
    router = ProviderRouter(primary=primary, max_retries_per_provider=2, max_backoff_seconds=0.1)
    task = AgentTask(goal="Test B", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Gemini Retry Success"


def test_scenario_c_gemini_429_grok_success():
    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"}]
    )
    grok = MockProviderScenario(
        "grok", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Grok Success"}]
    )
    router = ProviderRouter(primary=gemini, fallbacks=[grok], max_retries_per_provider=0)
    task = AgentTask(goal="Test C", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Grok Success"
    assert task.current_provider == "grok"


def test_scenario_d_gemini_429_grok_model_not_found_mistral_success():
    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"}]
    )
    grok = MockProviderScenario(
        "grok",
        [
            {
                "type": AgentDecisionType.FAIL,
                "error": "xAI API error 400 Model not found: grok-2-latest",
            }
        ],
    )
    mistral = MockProviderScenario(
        "mistral", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Mistral Success"}]
    )

    router = ProviderRouter(primary=gemini, fallbacks=[grok, mistral], max_retries_per_provider=0)
    task = AgentTask(goal="Test D", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])

    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Mistral Success"
    assert task.current_provider == "mistral"


def test_scenario_e_gemini_timeout_grok_success():
    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "Request failed: timeout"}]
    )
    grok = MockProviderScenario(
        "grok",
        [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Grok Timeout Fallback Success"}],
    )

    router = ProviderRouter(primary=gemini, fallbacks=[grok], max_retries_per_provider=0)
    task = AgentTask(goal="Test E", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])

    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Grok Timeout Fallback Success"
    assert task.current_provider == "grok"


def test_scenario_f_gemini_429_grok_500_mistral_success():
    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"}]
    )
    grok = MockProviderScenario(
        "grok", [{"type": AgentDecisionType.FAIL, "error": "500 Internal Server Error"}]
    )
    mistral = MockProviderScenario(
        "mistral",
        [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Mistral 500 Fallback Success"}],
    )

    router = ProviderRouter(primary=gemini, fallbacks=[grok, mistral], max_retries_per_provider=0)
    task = AgentTask(goal="Test F", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])

    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Mistral 500 Fallback Success"
    assert task.current_provider == "mistral"


def test_scenario_g_all_providers_fail():
    gemini = MockProviderScenario("gemini", [{"type": AgentDecisionType.FAIL, "error": "429"}])
    grok = MockProviderScenario("grok", [{"type": AgentDecisionType.FAIL, "error": "500"}])
    mistral = MockProviderScenario("mistral", [{"type": AgentDecisionType.FAIL, "error": "503"}])

    router = ProviderRouter(primary=gemini, fallbacks=[grok, mistral], max_retries_per_provider=0)
    task = AgentTask(goal="Test G", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])

    assert decision.type == AgentDecisionType.FAIL
    assert "All LLM providers in fallback chain failed" in decision.error_message


def test_scenario_h_i_provider_timeout_does_not_hang_loop():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    failing_router = ProviderRouter(
        primary=MockProviderScenario(
            "gemini", [{"type": AgentDecisionType.FAIL, "error": "timeout"}]
        ),
        fallbacks=[
            MockProviderScenario("grok", [{"type": AgentDecisionType.FAIL, "error": "timeout"}])
        ],
        max_retries_per_provider=0,
    )

    agent = AtlasAgent(provider=failing_router)
    task = AgentTask(goal="Test Timeout Bound", granted_permissions=[AgentPermission.READ])
    completed_task = agent.run_task(task, db)

    assert completed_task.status == AgentTaskStatus.FAILED
    assert completed_task.status != AgentTaskStatus.EXECUTING


def test_scenario_j_k_full_workflow_and_lineage_isolation():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    workflow_responses = [
        {
            "type": AgentDecisionType.TOOL_CALL,
            "tool_name": "create_benchmark",
            "arguments": {"name": "Math Benchmark"},
        },
        {
            "type": AgentDecisionType.TOOL_CALL,
            "tool_name": "create_dataset",
            "arguments": {
                "benchmark_id": "bm-1",
                "name": "Math DS",
                "tasks": [{"input": "1+2", "expected_output": "3"}],
            },
        },
        {
            "type": AgentDecisionType.TOOL_CALL,
            "tool_name": "create_evaluation_case",
            "arguments": {
                "dataset_id": "ds-1",
                "evaluation_cases": [{"task_id": "t1", "expected_answer": "3"}],
            },
        },
        {
            "type": AgentDecisionType.TOOL_CALL,
            "tool_name": "validate_benchmark_dataset",
            "arguments": {"dataset_id": "ds-1"},
        },
        {
            "type": AgentDecisionType.TOOL_CALL,
            "tool_name": "run_benchmark",
            "arguments": {
                "benchmark_version_id": "bmv-1",
                "dataset_id": "ds-1",
                "target_models": ["gemini-3.5-flash-lite"],
            },
        },
        {
            "type": AgentDecisionType.TOOL_CALL,
            "tool_name": "evaluate_run",
            "arguments": {"execution_id": "exec-1"},
        },
        {
            "type": AgentDecisionType.TOOL_CALL,
            "tool_name": "generate_report",
            "arguments": {"benchmark_id": "bm-1", "execution_id": "exec-1", "summary": "100% Pass"},
        },
    ]

    provider = MockProviderScenario("mock_workflow", workflow_responses)
    agent = AtlasAgent(provider=provider)
    task = AgentTask(
        goal="Create Math Benchmark",
        granted_permissions=[
            AgentPermission.READ,
            AgentPermission.WRITE,
            AgentPermission.EXECUTE,
            AgentPermission.PUBLISH,
        ],
    )

    completed_task = agent.run_task(task, db)

    assert completed_task.status == AgentTaskStatus.COMPLETED
    assert completed_task.benchmark_id is not None
    assert completed_task.dataset_id is not None
    assert len(completed_task.execution_ids) == 1
    assert completed_task.report_id is not None


def test_regression_prose_decision_rejection_and_repair():
    """
    Part 9 Regression Test:
    Gemini 429 -> Grok 400 -> Mistral 1st response prose ("I need to create...") ->
    Decision rejected & repaired -> Mistral 2nd response tool_call -> task continues.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 Rate limit"}]
    )
    grok = MockProviderScenario(
        "grok", [{"type": AgentDecisionType.FAIL, "error": "400 Model not found"}]
    )
    mistral = MockProviderScenario(
        "mistral",
        [
            {
                "type": AgentDecisionType.FINAL_RESPONSE,
                "response": "I need to create the benchmark specification first.",
            },
            {
                "type": AgentDecisionType.TOOL_CALL,
                "tool_name": "create_benchmark",
                "arguments": {"name": "Math Benchmark"},
            },
            {
                "type": AgentDecisionType.TOOL_CALL,
                "tool_name": "create_dataset",
                "arguments": {
                    "benchmark_id": "bm-1",
                    "name": "Math DS",
                    "tasks": [{"input": "1+2", "expected_output": "3"}],
                },
            },
            {
                "type": AgentDecisionType.TOOL_CALL,
                "tool_name": "create_evaluation_case",
                "arguments": {
                    "dataset_id": "ds-1",
                    "evaluation_cases": [{"task_id": "t1", "expected_answer": "3"}],
                },
            },
            {
                "type": AgentDecisionType.TOOL_CALL,
                "tool_name": "validate_benchmark_dataset",
                "arguments": {"dataset_id": "ds-1"},
            },
            {
                "type": AgentDecisionType.TOOL_CALL,
                "tool_name": "run_benchmark",
                "arguments": {
                    "benchmark_version_id": "bmv-1",
                    "dataset_id": "ds-1",
                    "target_models": ["gemini-3.5-flash-lite"],
                },
            },
            {
                "type": AgentDecisionType.TOOL_CALL,
                "tool_name": "evaluate_run",
                "arguments": {"execution_id": "exec-1"},
            },
            {
                "type": AgentDecisionType.TOOL_CALL,
                "tool_name": "generate_report",
                "arguments": {
                    "benchmark_id": "bm-1",
                    "execution_id": "exec-1",
                    "summary": "100% Pass",
                },
            },
        ],
    )

    router = ProviderRouter(primary=gemini, fallbacks=[grok, mistral], max_retries_per_provider=0)
    agent = AtlasAgent(provider=router)
    task = AgentTask(
        goal="Create Math Benchmark",
        granted_permissions=[
            AgentPermission.READ,
            AgentPermission.WRITE,
            AgentPermission.EXECUTE,
            AgentPermission.PUBLISH,
        ],
    )

    completed_task = agent.run_task(task, db)

    assert completed_task.status == AgentTaskStatus.COMPLETED
    assert completed_task.benchmark_id is not None
    assert completed_task.dataset_id is not None
    assert any(
        (getattr(t, "event_type", t.get("event_type") if isinstance(t, dict) else None))
        == "DECISION_REJECTED_PROSE"
        for t in completed_task.execution_trace
    )


def test_regression_repeated_prose_fails_task_not_completed():
    """
    Part 10 Regression Test:
    Gemini 429 -> Grok 400 -> Mistral 1st response prose -> Repair -> Mistral 2nd response prose again ->
    Task MUST transition to FAILED, NEVER COMPLETED.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 Rate limit"}]
    )
    grok = MockProviderScenario(
        "grok", [{"type": AgentDecisionType.FAIL, "error": "400 Model not found"}]
    )
    mistral = MockProviderScenario(
        "mistral",
        [
            {
                "type": AgentDecisionType.FINAL_RESPONSE,
                "response": "I need to create the benchmark specification first.",
            },
            {
                "type": AgentDecisionType.FINAL_RESPONSE,
                "response": "I will create a benchmark soon.",
            },
        ],
    )

    router = ProviderRouter(primary=gemini, fallbacks=[grok, mistral], max_retries_per_provider=0)
    agent = AtlasAgent(provider=router)
    task = AgentTask(
        goal="Create Math Benchmark",
        granted_permissions=[AgentPermission.READ, AgentPermission.WRITE],
    )

    completed_task = agent.run_task(task, db)

    assert completed_task.status == AgentTaskStatus.FAILED
    assert completed_task.status != AgentTaskStatus.COMPLETED
    assert "conversational text instead of executable tool call" in (
        completed_task.error_detail or ""
    )


def test_regression_request_clarification_flow():
    """
    Verify request_clarification tool call suspends the task and transitions to WAITING_FOR_CLARIFICATION.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    workflow_responses = [
        {
            "type": AgentDecisionType.TOOL_CALL,
            "tool_name": "request_clarification",
            "arguments": {"question": "Should we test addition or subtraction?"},
        }
    ]

    provider = MockProviderScenario("mock_clarify", workflow_responses)
    agent = AtlasAgent(provider=provider)
    task = AgentTask(
        goal="make a custom benchmark",
        granted_permissions=[AgentPermission.READ, AgentPermission.WRITE],
    )

    suspended_task = agent.run_task(task, db)

    assert suspended_task.status == AgentTaskStatus.WAITING_FOR_CLARIFICATION
    assert suspended_task.clarification_prompt == "Should we test addition or subtraction?"
    assert any(
        getattr(e, "event_type", None) == "WAITING_FOR_CLARIFICATION"
        for e in suspended_task.execution_trace
    )


def test_adaptive_plan_generation():
    """
    Verify plan generation dynamically adapts based on goal string keywords.
    """
    agent = AtlasAgent(provider=MockProviderScenario("mock", []))

    # Creation only benchmark
    task_create = AgentTask(goal="Create a benchmark for model safety")
    task_create.plan = agent.planner.generate_initial_plan(task_create.goal)
    assert len(task_create.plan) == 4
    assert task_create.plan[0].description == "Define benchmark specification"
    assert task_create.plan[-1].description == "Validate task formats and completeness"

    # Full evaluation benchmark
    task_full = AgentTask(goal="Create and run a benchmark comparing models on math")
    task_full.plan = agent.planner.generate_initial_plan(task_full.goal)
    assert len(task_full.plan) == 7
    assert task_full.plan[-1].description == "Publish comparative benchmark report"


def test_cooldown_skip_emits_provider_fallback_trace():
    """
    Regression: when a provider is skipped because its cooldown is active,
    the execution trace MUST contain a provider_fallback event explaining
    the skip and the next provider the router advanced to.
    """
    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Gemini Ok"}]
    )
    groq = MockProviderScenario(
        "groq", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Groq Ok"}]
    )
    router = ProviderRouter(primary=gemini, fallbacks=[groq], max_retries_per_provider=0)
    task = AgentTask(goal="Cooldown trace", granted_permissions=[AgentPermission.READ])

    # Force gemini into cooldown as if it had failed recently.
    router._provider_cooldowns["gemini"] = __import__("time").time() + 300.0

    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Groq Ok"
    assert task.current_provider == "groq"

    fallback_events = [e for e in task.execution_trace if e.event_type == "provider_fallback"]
    assert len(fallback_events) == 1
    details = fallback_events[0].details
    assert details["failed_provider"] == "gemini"
    assert details["next_provider"] == "groq"
    assert "cooldown" in details["reason"].lower()
    assert gemini.call_count == 0


def test_unhealthy_skip_emits_provider_fallback_trace():
    """
    Regression: when a provider is skipped because its health check fails
    (missing API key), the execution trace MUST contain a provider_fallback
    event explaining the skip and the next provider.
    """

    class _UnhealthyProvider(BaseLLMProvider):
        name = "gemini"
        model = "gemini-3.5-flash-lite"

        class _Client:
            def health(self):
                return False

        client = _Client()

        def decide(self, task, prompt_context, available_tools):
            raise AssertionError("Unhealthy provider should never be called")

    groq = MockProviderScenario(
        "groq", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Groq Ok"}]
    )
    router = ProviderRouter(
        primary=_UnhealthyProvider(), fallbacks=[groq], max_retries_per_provider=0
    )
    task = AgentTask(goal="Unhealthy trace", granted_permissions=[AgentPermission.READ])

    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Groq Ok"
    assert task.current_provider == "groq"

    fallback_events = [e for e in task.execution_trace if e.event_type == "provider_fallback"]
    assert len(fallback_events) == 1
    details = fallback_events[0].details
    assert details["failed_provider"] == "gemini"
    assert details["next_provider"] == "groq"
    assert "unhealthy" in details["reason"].lower() or "missing" in details["reason"].lower()


def test_retry_exhaustion_emits_provider_fallback_trace():
    """
    Regression: when a provider exhausts its retries on a RETRYABLE error,
    the execution trace MUST contain a provider_fallback event when the
    router advances to the next provider.
    """
    gemini = MockProviderScenario(
        "gemini", [{"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"}]
    )
    groq = MockProviderScenario(
        "groq", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Groq Ok"}]
    )
    router = ProviderRouter(primary=gemini, fallbacks=[groq], max_retries_per_provider=0)
    task = AgentTask(goal="Retry exhaustion trace", granted_permissions=[AgentPermission.READ])

    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Groq Ok"
    assert task.current_provider == "groq"

    fallback_events = [e for e in task.execution_trace if e.event_type == "provider_fallback"]
    assert len(fallback_events) == 1
    details = fallback_events[0].details
    assert details["failed_provider"] == "gemini"
    assert details["next_provider"] == "groq"
    assert "429" in details["reason"]


def test_exception_retry_exhaustion_emits_provider_fallback_trace():
    """
    Regression: when a provider raises exceptions that exhaust retries, the
    execution trace MUST contain a provider_fallback event when the router
    advances to the next provider.
    """

    class _RaisingProvider(BaseLLMProvider):
        name = "gemini"
        model = "gemini-3.5-flash-lite"

        def decide(self, task, prompt_context, available_tools):
            raise ConnectionError("connection failure: upstream timeout")

    groq = MockProviderScenario(
        "groq", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Groq Ok"}]
    )
    router = ProviderRouter(
        primary=_RaisingProvider(), fallbacks=[groq], max_retries_per_provider=0
    )
    task = AgentTask(goal="Exception exhaustion trace", granted_permissions=[AgentPermission.READ])

    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Groq Ok"
    assert task.current_provider == "groq"

    fallback_events = [e for e in task.execution_trace if e.event_type == "provider_fallback"]
    assert len(fallback_events) == 1
    details = fallback_events[0].details
    assert details["failed_provider"] == "gemini"
    assert details["next_provider"] == "groq"
