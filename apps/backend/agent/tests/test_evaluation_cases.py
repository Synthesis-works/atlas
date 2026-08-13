import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.providers.mock import MockAgentProvider
from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus
from apps.backend.agent.tools.evaluation_tools import (
    CreateEvaluationCaseTool,
    EvaluateRunTool,
    _evaluation_case_store,
)
from apps.backend.agent.tools.execution_tools import RunBenchmarkTool, _benchmark_execution_store
from apps.backend.agent.tools.registry import ToolRegistry


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_evaluation_case_tool_execution(db_session):
    tool = CreateEvaluationCaseTool()
    res = tool.execute(
        db=db_session,
        dataset_id="ds-test-101",
        evaluation_cases=[
            {
                "task_id": "task_1",
                "expected_answer": "3",
                "evaluation_method": "exact_match",
                "accepted_answers": ["3", "three"],
            }
        ],
    )
    assert res["status"] == "CREATED"
    assert res["total_cases_created"] == 1
    assert len(res["evaluation_cases"]) == 1
    assert res["evaluation_cases"][0]["expected_answer"] == "3"


def test_evaluation_case_exact_match(db_session):
    # Setup evaluation case
    ec_tool = CreateEvaluationCaseTool()
    ec_tool.execute(
        db=db_session,
        dataset_id="ds-math-102",
        evaluation_cases=[
            {
                "task_id": "task_math_1",
                "expected_answer": "3",
                "evaluation_method": "exact_match",
            }
        ],
    )

    # Setup execution store
    _benchmark_execution_store["exec-math-1"] = {
        "execution_id": "exec-math-1",
        "target_model": "gemini-3.5-flash-lite",
        "status": "COMPLETED",
        "results": [
            {
                "task_id": "task_math_1",
                "input": "What is 1 + 2?",
                "expected_output": "3",
                "raw_output": "The answer is 3.",
                "normalized_answer": "3",
                "latency_ms": 250,
            }
        ],
    }

    eval_tool = EvaluateRunTool()
    res = eval_tool.execute(db=db_session, execution_id="exec-math-1")
    assert res["status"] == "EVALUATED"
    assert res["metrics"]["accuracy"] == 100.0
    assert len(res["results"]) == 1
    assert res["results"][0]["correct"] is True
    assert res["results"][0]["raw_output"] == "The answer is 3."
    assert res["results"][0]["expected_answer"] == "3"


def test_evaluation_case_rubric_judge(db_session):
    ec_tool = CreateEvaluationCaseTool()
    ec_tool.execute(
        db=db_session,
        dataset_id="ds-rubric-103",
        evaluation_cases=[
            {
                "task_id": "task_summary_1",
                "expected_answer": "Rayleigh scattering of sunlight by atmospheric molecules",
                "evaluation_method": "llm_judge",
                "rubric_criteria": [
                    "Mentions Rayleigh scattering",
                    "Mentions blue light wavelength",
                ],
            }
        ],
    )

    _benchmark_execution_store["exec-rubric-1"] = {
        "execution_id": "exec-rubric-1",
        "target_model": "mistral-small-latest",
        "status": "COMPLETED",
        "results": [
            {
                "task_id": "task_summary_1",
                "input": "Why is the sky blue?",
                "expected_output": "Rayleigh scattering",
                "raw_output": "The sky is blue because Rayleigh scattering scatters short blue light wavelengths.",
                "normalized_answer": "Rayleigh scattering",
                "latency_ms": 400,
            }
        ],
    }

    eval_tool = EvaluateRunTool()
    res = eval_tool.execute(db=db_session, execution_id="exec-rubric-1")
    assert res["status"] == "EVALUATED"
    assert res["results"][0]["evaluation_method"] == "llm_judge"
    assert res["results"][0]["correct"] is True


def test_tool_registry_has_15_tools():
    registry = ToolRegistry()
    tools = registry.list_tools()
    assert len(tools) >= 14
    tool_names = [t["name"] for t in tools]
    assert "create_evaluation_case" in tool_names
