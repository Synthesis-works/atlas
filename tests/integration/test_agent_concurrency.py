import pytest
import threading
import time
from fastapi.testclient import TestClient

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

def test_c1_simultaneous_runs():
    """
    Test C1: Two simultaneous runs do not interfere.
    Since mock provider is synchronous, we run them in separate threads.
    """
    results = {}

    def run_task(idx):
        payload = {
            "goal": f"Task {idx}: Create benchmark, dataset, evaluate and report.",
            "provider": "mock",
            "permissions": ["READ", "WRITE", "EXECUTE", "PUBLISH"],
        }
        resp = client.post("/api/v1/agent/tasks", json=payload)
        results[idx] = resp.json()

    t1 = threading.Thread(target=run_task, args=(1,))
    t2 = threading.Thread(target=run_task, args=(2,))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

    # Both should have completed
    assert results[1]["status"] == "COMPLETED"
    assert results[2]["status"] == "COMPLETED"

    # Both should have different UUIDs
    assert results[1]["task_id"] != results[2]["task_id"]
    assert results[1]["benchmark_id"] != results[2]["benchmark_id"]
    
def test_c2_clarification_isolation():
    """
    Test C2: Clarification isolation. 
    Task 1 pauses for clarification. Task 2 starts and completes without affecting Task 1.
    """
    payload1 = {
        "goal": "Need clarification test",
        "provider": "mock",
        "permissions": ["READ", "WRITE", "EXECUTE", "PUBLISH"],
    }
    resp1 = client.post("/api/v1/agent/tasks", json=payload1)
    task1 = resp1.json()
    assert task1["status"] == "WAITING_FOR_CLARIFICATION"

    # Now run Task 2 fully
    payload2 = {
        "goal": "Create a benchmark and report.",
        "provider": "mock",
        "permissions": ["READ", "WRITE", "EXECUTE", "PUBLISH"],
    }
    resp2 = client.post("/api/v1/agent/tasks", json=payload2)
    task2 = resp2.json()
    assert task2["status"] == "COMPLETED"

    # Check Task 1 is STILL waiting
    poll1 = client.get(f"/api/v1/agent/tasks/{task1['task_id']}").json()
    assert poll1["status"] == "WAITING_FOR_CLARIFICATION"

    # Resume Task 1
    clarify_resp = client.post(
        f"/api/v1/agent/tasks/{task1['task_id']}/clarify",
        json={"clarification_id": task1["clarification_id"], "answer": "Use addition"}
    )
    assert clarify_resp.status_code == 200

    poll1_end = client.get(f"/api/v1/agent/tasks/{task1['task_id']}").json()
    assert poll1_end["status"] == "COMPLETED"
    assert poll1_end["task_id"] != task2["task_id"]

def test_c4_adversarial_dataset_isolation():
    """
    Test C4: Adversarial dataset isolation (Execution Engine lineage check).
    """
    from uuid import uuid4
    import uuid
    # Using random UUIDs that don't have associated test cases
    fake_bv_id = uuid4()
    fake_dv_id = uuid4()
    
    from atlas_db.models.execution import Execution as DBExecution
    from apps.backend.worker.execution_runner import ExecutionRunner
    from atlas_db.core.session import SessionLocal
    
    db = SessionLocal()
    try:
        db_exec = DBExecution(
            id=uuid4(),
            project_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            benchmark_version_id=fake_bv_id,
            dataset_version_id=fake_dv_id,
            submitted_by_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            target_model="gemini-3.5-flash-lite",
            status="QUEUED"
        )
        db.add(db_exec)
        db.commit()
        db.refresh(db_exec)
        
        runner = ExecutionRunner(db=db)
        with pytest.raises(ValueError) as runner_exc:
            runner.run(db_exec)
            
        assert "No test cases found for dataset_version_id" in str(runner_exc.value)
    finally:
        db.close()
