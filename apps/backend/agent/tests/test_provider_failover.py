import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.router import ProviderRouter
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentPermission, AgentTask, AgentTaskStatus
from apps.backend.agent.tools.registry import ToolRegistry


class MockProviderScenario(BaseLLMProvider):
    def __init__(self, name: str, responses: list[dict]):
        self.name = name
        self.responses = list(responses)
        self.call_count = 0

    def decide(self, task: AgentTask, prompt_context: str, available_tools: list) -> AgentDecision:
        self.call_count += 1
        if not self.responses:
            return AgentDecision(type=AgentDecisionType.FAIL, error_message=f"{self.name} out of responses")
        
        curr = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        dtype = curr.get("type", AgentDecisionType.FAIL)
        
        if dtype == AgentDecisionType.FAIL:
            return AgentDecision(type=dtype, error_message=curr.get("error", "Error"))
        elif dtype == AgentDecisionType.TOOL_CALL:
            return AgentDecision(type=dtype, tool_name=curr.get("tool_name"), arguments=curr.get("arguments", {}))
        else:
            return AgentDecision(type=dtype, response=curr.get("response", "Done"))


def test_scenario_a_gemini_success():
    primary = MockProviderScenario("gemini", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Gemini Ok"}])
    router = ProviderRouter(primary=primary)
    task = AgentTask(goal="Test A", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Gemini Ok"
    assert task.current_provider == "gemini"


def test_scenario_b_gemini_429_retry_success():
    primary = MockProviderScenario("gemini", [
        {"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"},
        {"type": AgentDecisionType.FINAL_RESPONSE, "response": "Gemini Retry Success"}
    ])
    router = ProviderRouter(primary=primary, max_retries_per_provider=2, max_backoff_seconds=0.1)
    task = AgentTask(goal="Test B", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Gemini Retry Success"


def test_scenario_c_gemini_429_grok_success():
    gemini = MockProviderScenario("gemini", [{"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"}])
    grok = MockProviderScenario("grok", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Grok Success"}])
    router = ProviderRouter(primary=gemini, fallbacks=[grok], max_retries_per_provider=0)
    task = AgentTask(goal="Test C", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Grok Success"
    assert task.current_provider == "grok"


def test_scenario_d_gemini_429_grok_model_not_found_mistral_success():
    gemini = MockProviderScenario("gemini", [{"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"}])
    grok = MockProviderScenario("grok", [{"type": AgentDecisionType.FAIL, "error": "xAI API error 400 Model not found: grok-2-latest"}])
    mistral = MockProviderScenario("mistral", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Mistral Success"}])
    
    router = ProviderRouter(primary=gemini, fallbacks=[grok, mistral], max_retries_per_provider=0)
    task = AgentTask(goal="Test D", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])
    
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Mistral Success"
    assert task.current_provider == "mistral"


def test_scenario_e_gemini_timeout_grok_success():
    gemini = MockProviderScenario("gemini", [{"type": AgentDecisionType.FAIL, "error": "Request failed: timeout"}])
    grok = MockProviderScenario("grok", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Grok Timeout Fallback Success"}])
    
    router = ProviderRouter(primary=gemini, fallbacks=[grok], max_retries_per_provider=0)
    task = AgentTask(goal="Test E", granted_permissions=[AgentPermission.READ])
    decision = router.decide(task, "ctx", [])
    
    assert decision.type == AgentDecisionType.FINAL_RESPONSE
    assert decision.response == "Grok Timeout Fallback Success"
    assert task.current_provider == "grok"


def test_scenario_f_gemini_429_grok_500_mistral_success():
    gemini = MockProviderScenario("gemini", [{"type": AgentDecisionType.FAIL, "error": "429 RESOURCE_EXHAUSTED"}])
    grok = MockProviderScenario("grok", [{"type": AgentDecisionType.FAIL, "error": "500 Internal Server Error"}])
    mistral = MockProviderScenario("mistral", [{"type": AgentDecisionType.FINAL_RESPONSE, "response": "Mistral 500 Fallback Success"}])
    
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
        primary=MockProviderScenario("gemini", [{"type": AgentDecisionType.FAIL, "error": "timeout"}]),
        fallbacks=[MockProviderScenario("grok", [{"type": AgentDecisionType.FAIL, "error": "timeout"}])],
        max_retries_per_provider=0
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
        {"type": AgentDecisionType.TOOL_CALL, "tool_name": "create_benchmark", "arguments": {"name": "Math Benchmark"}},
        {"type": AgentDecisionType.TOOL_CALL, "tool_name": "create_dataset", "arguments": {"benchmark_id": "bm-1", "name": "Math DS", "tasks": [{"input": "1+2", "expected_output": "3"}]}},
        {"type": AgentDecisionType.TOOL_CALL, "tool_name": "create_evaluation_case", "arguments": {"dataset_id": "ds-1", "evaluation_cases": [{"task_id": "t1", "expected_answer": "3"}]}},
        {"type": AgentDecisionType.TOOL_CALL, "tool_name": "validate_benchmark_dataset", "arguments": {"dataset_id": "ds-1"}},
        {"type": AgentDecisionType.TOOL_CALL, "tool_name": "run_benchmark", "arguments": {"benchmark_version_id": "bmv-1", "dataset_id": "ds-1", "target_models": ["gemini-3.5-flash-lite"]}},
        {"type": AgentDecisionType.TOOL_CALL, "tool_name": "evaluate_run", "arguments": {"execution_id": "exec-1"}},
        {"type": AgentDecisionType.TOOL_CALL, "tool_name": "generate_report", "arguments": {"benchmark_id": "bm-1", "execution_id": "exec-1", "summary": "100% Pass"}},
    ]

    provider = MockProviderScenario("mock_workflow", workflow_responses)
    agent = AtlasAgent(provider=provider)
    task = AgentTask(goal="Create Math Benchmark", granted_permissions=[AgentPermission.READ, AgentPermission.WRITE, AgentPermission.EXECUTE, AgentPermission.PUBLISH])
    
    completed_task = agent.run_task(task, db)
    
    assert completed_task.status == AgentTaskStatus.COMPLETED
    assert completed_task.benchmark_id is not None
    assert completed_task.dataset_id is not None
    assert len(completed_task.execution_ids) == 1
    assert completed_task.report_id is not None
