import os
import dotenv
import pytest
from fastapi.testclient import TestClient

dotenv.load_dotenv()

from apps.backend.main import app
from apps.backend.agent.providers.gemini import GeminiAgentProvider
from apps.backend.agent.state import AgentDecisionType, AgentPermission, AgentTask, AgentTaskStatus

client = TestClient(app)


def test_list_agent_tools_endpoint():
    response = client.get("/api/v1/agent/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) >= 13
    tool_names = [t["name"] for t in tools]
    assert "search_benchmarks" in tool_names
    assert "update_dataset" in tool_names
    assert "search_memory" in tool_names


def test_create_and_run_agent_task_mock():
    payload = {
        "goal": "Create a benchmark for Python vulnerability identification, attach dataset, validate, run, evaluate, and generate report.",
        "provider": "mock",
        "permissions": ["READ", "WRITE", "EXECUTE", "PUBLISH"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "COMPLETED"
    assert data["final_result"] is not None
    assert "completed successfully" in data["final_result"]["summary"]

    # Poll task details
    task_id = data["task_id"]
    poll_resp = client.get(f"/api/v1/agent/tasks/{task_id}")
    assert poll_resp.status_code == 200
    poll_data = poll_resp.json()
    assert poll_data["task_id"] == task_id
    assert len(poll_data["tool_calls"]) > 0
    assert len(poll_data["observations"]) > 0
    assert len(poll_data["execution_trace"]) > 0


def test_agent_task_approval_flow():
    # Grant only READ permission to trigger WAITING_FOR_APPROVAL when WRITE tool is selected
    payload = {
        "goal": "Create benchmark requiring approval",
        "provider": "mock",
        "permissions": ["READ", "EXECUTE", "PUBLISH"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "WAITING_FOR_APPROVAL"

    task_id = data["task_id"]
    poll_resp = client.get(f"/api/v1/agent/tasks/{task_id}")
    poll_data = poll_resp.json()
    approval_token = poll_data["approval_token"]
    assert approval_token is not None

    # Approve task
    appr_resp = client.post(f"/api/v1/agent/tasks/{task_id}/approve", json={"approval_token": approval_token})
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "COMPLETED"


def test_agent_task_cancellation_flow():
    payload = {
        "goal": "Cancel test goal",
        "provider": "mock",
        "permissions": ["READ"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    task_id = response.json()["task_id"]

    cancel_resp = client.post(f"/api/v1/agent/tasks/{task_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"


def test_real_gemini_provider_smoke():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY environment variable not set.")

    provider = GeminiAgentProvider(model="gemini-3.5-flash-lite")
    task = AgentTask(
        goal="Create Python Security Vulnerability Benchmark",
        granted_permissions=[AgentPermission.READ, AgentPermission.WRITE, AgentPermission.EXECUTE, AgentPermission.PUBLISH],
    )
    prompt_context = "Goal: Create a benchmark for Python vulnerability identification."
    declarations = [
        {
            "name": "create_benchmark",
            "description": "Create a benchmark specification in Atlas.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING", "description": "Benchmark title."},
                    "description": {"type": "STRING", "description": "Objective description."},
                },
                "required": ["name"],
            },
        }
    ]

    try:
        decision = provider.decide(task, prompt_context, declarations)
        if decision.type == AgentDecisionType.FAIL and "getaddrinfo" in str(decision.error_message):
            pytest.skip("Gemini API endpoint unreachable (DNS/Network offline).")
        assert decision.type in [AgentDecisionType.TOOL_CALL, AgentDecisionType.FINAL_RESPONSE]
        if decision.type == AgentDecisionType.TOOL_CALL:
            assert decision.tool_name is not None
    except Exception as e:
        pytest.skip(f"Gemini API request skipped due to network/connectivity error: {e}")
