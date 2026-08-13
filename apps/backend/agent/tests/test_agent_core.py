from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.memory import SemanticMemoryStore
from apps.backend.agent.providers.mock import MockAgentProvider
from apps.backend.agent.state import (
    MAX_REPAIR_ATTEMPTS,
    MAX_STEPS,
    MAX_TOOL_CALLS,
    AgentPermission,
    AgentTask,
    AgentTaskStatus,
)
from apps.backend.agent.tools.registry import ToolRegistry


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_tool_registry_tools():
    registry = ToolRegistry()
    tools = registry.list_tools()
    assert len(tools) >= 13

    declarations = registry.get_gemini_declarations()
    assert len(declarations) >= 13
    assert any(d["name"] == "search_memory" for d in declarations)
    assert any(d["name"] == "update_dataset" for d in declarations)


def test_tool_permission_enforcement():
    registry = ToolRegistry()
    granted = [AgentPermission.READ]

    assert registry.check_permission("search_benchmarks", granted) is True
    assert registry.check_permission("create_benchmark", granted) is False
    assert registry.check_permission("run_benchmark", granted) is False


def test_mock_agent_full_workflow(db_session):
    agent = AtlasAgent(provider=MockAgentProvider())
    task = AgentTask(
        goal="Create Python Security Vulnerability Benchmark",
        granted_permissions=[
            AgentPermission.READ,
            AgentPermission.WRITE,
            AgentPermission.EXECUTE,
            AgentPermission.PUBLISH,
        ],
    )

    agent.run_task(task, db_session)

    assert task.status == AgentTaskStatus.COMPLETED
    assert task.final_result is not None
    assert "completed successfully" in task.final_result["summary"]
    assert task.step_count > 0
    assert task.total_tool_calls > 0
    assert len(task.observations) > 0


def test_hard_limit_max_steps(db_session):
    agent = AtlasAgent(provider=MockAgentProvider())
    task = AgentTask(goal="Limit test", granted_permissions=[AgentPermission.READ])
    task.step_count = MAX_STEPS  # Force max steps hit

    agent.run_task(task, db_session)

    assert task.status == AgentTaskStatus.FAILED
    assert "MAX_STEPS" in task.error_detail


def test_hard_limit_max_tool_calls(db_session):
    agent = AtlasAgent(provider=MockAgentProvider())
    task = AgentTask(goal="Tool limit test", granted_permissions=[AgentPermission.READ])
    task.total_tool_calls = MAX_TOOL_CALLS

    agent.run_task(task, db_session)

    assert task.status == AgentTaskStatus.FAILED
    assert "MAX_TOOL_CALLS" in task.error_detail


def test_semantic_memory_offline_fallback():
    store = SemanticMemoryStore(base_url="http://localhost:99999")  # Non-existent port
    assert store.is_available is False

    res = store.search("anything")
    assert res == []
