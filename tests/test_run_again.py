import pytest
from fastapi.testclient import TestClient
from uuid import UUID

from apps.backend.main import app
from apps.backend.routers.agent import _agent_tasks_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    from atlas_db.core.engine import engine

    if "sqlite" in str(engine.url):
        from atlas_db.core.initialize import initialize_database_schema

        initialize_database_schema(engine)
    _agent_tasks_db.clear()


def test_agent_run_again_flow():
    # 1. Start normal benchmark task
    payload = {
        "goal": "Create a benchmark for vulnerability identification and publish comparative report.",
        "provider": "mock",
        "permissions": ["READ", "WRITE", "EXECUTE", "PUBLISH"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    source_task = response.json()
    source_id = source_task["task_id"]
    assert source_task["status"] == "COMPLETED"

    # Get detailed state of source task
    source_detail = client.get(f"/api/v1/agent/tasks/{source_id}").json()
    assert source_detail["report_id"] is not None

    # 2. Trigger Run Again
    rerun_resp = client.post(f"/api/v1/agent/tasks/{source_id}/run-again")
    assert rerun_resp.status_code == 200
    rerun_data = rerun_resp.json()
    rerun_id = rerun_data["task_id"]
    assert rerun_id != source_id
    assert rerun_data["status"] == "COMPLETED"

    # 3. Retrieve and inspect rerun task details
    rerun_detail = client.get(f"/api/v1/agent/tasks/{rerun_id}").json()

    # Assert reuse of configurations
    assert rerun_detail["run_mode"] == "RERUN"
    assert rerun_detail["source_task_id"] == source_id
    assert rerun_detail["benchmark_id"] == source_detail["benchmark_id"]
    assert rerun_detail["benchmark_version_id"] == source_detail["benchmark_version_id"]
    assert rerun_detail["dataset_id"] == source_detail["dataset_id"]
    assert rerun_detail["dataset_version_id"] == source_detail["dataset_version_id"]

    # Assert new execution and report lineage
    assert rerun_detail["report_id"] is not None
    assert rerun_detail["report_id"] != source_detail["report_id"]

    # Assert that tool execution history contains the execution steps, not the copied creation steps
    called_tools = [c["tool_name"] for c in rerun_detail["tool_calls"]]
    assert "create_benchmark" not in called_tools
    assert "create_dataset" not in called_tools
    assert "run_benchmark" in called_tools
    assert "evaluate_run" in called_tools
    assert "generate_report" in called_tools

    # 4. Verify DB records and lineage via direct DB inspection
    from atlas_db.core.session import SessionLocal
    from sqlalchemy import text

    with SessionLocal() as db:
        # Retrieve report version
        ver_row = db.execute(
            text(
                "SELECT id, report_id, execution_id FROM report_versions WHERE id = :report_version_id"
            ),
            {"report_version_id": rerun_detail["report_id"].replace("-", "")},
        ).fetchone()
        assert ver_row is not None
        assert str(ver_row.id).replace("-", "") == rerun_detail["report_id"].replace("-", "")
        assert str(ver_row.execution_id).replace("-", "") in [
            eid.replace("-", "") for eid in rerun_detail["execution_ids"]
        ]

        # Retrieve new report
        rep_row = db.execute(
            text("SELECT id, name, project_id FROM reports WHERE id = :report_id"),
            {"report_id": ver_row.report_id},
        ).fetchone()
        assert rep_row is not None
        assert rep_row.id == ver_row.report_id


def test_stuck_agent_progress_invariant():
    from apps.backend.agent.agent import AtlasAgent
    from apps.backend.agent.state import (
        AgentTask,
        AgentTaskStatus,
        AgentDecision,
        AgentDecisionType,
    )
    from apps.backend.agent.providers.base import BaseLLMProvider
    from atlas_db.core.session import SessionLocal

    class StuckLLMProvider(BaseLLMProvider):
        def decide(self, task, context, declarations) -> AgentDecision:
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="get_available_models",
                arguments={},
                reasoning="Simulating stuck behavior by calling get_available_models repeatedly.",
            )

    task = AgentTask(
        goal="Simulate a stuck agent run.",
        primary_provider="mock",
    )

    agent = AtlasAgent(provider=StuckLLMProvider())

    with SessionLocal() as db:
        run_task = agent.run_task(task, db)

    assert run_task.status == AgentTaskStatus.FAILED
    assert "Plan-Progress Invariant Violation" in run_task.error_detail
    assert run_task.step_count == 5
    assert run_task.consecutive_non_progress_steps == 4
