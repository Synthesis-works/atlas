"""Regression tests: agent task mutations must work across backend instances.

Before this change, approve/cancel/clarify/run-again resolved tasks only from
the process-local ``_agent_tasks_db`` registry. On a multi-instance deployment
(Vercel serverless) that produced 404s for tasks created/parked on a different
instance — exactly the "AgentTask ... not found" errors observed on the live
site. The persisted ``agent_task_records`` snapshot is now the source of truth
for every mutation, so this suite simulates "another instance" by removing the
task from the local registry and expects every operation to still succeed.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_db():
    from atlas_db.core.engine import engine

    if "sqlite" in str(engine.url):
        from atlas_db.core.initialize import initialize_database_schema

        initialize_database_schema(engine)
    from apps.backend.routers.agent import _agent_tasks_db

    _agent_tasks_db.clear()


from apps.backend.main import app  # noqa: E402

client = TestClient(app)

# A resumed mock loop legitimately parks at WAITING_FOR_EXECUTION when no
# execution backend (docker / GitHub Actions) resolves the run inside the
# test process; COMPLETED requires a live worker stack. The regression these
# tests guard is cross-instance *mutation from the persisted snapshot*, so
# resolve to any post-resume state.
RESUME_LEAF_STATUSES = {
    "PLANNING",
    "EXECUTING",
    "WAITING_FOR_EXECUTION",
    "COMPLETED",
    "REPORTING",
    "EVALUATING",
}


def _drop_local_only(task_id) -> None:
    """Simulate the task living on a *different* instance by removing it
    from THIS process's registry; only the DB snapshot remains."""
    from apps.backend.routers.agent import _agent_tasks_db
    from uuid import UUID

    uid = UUID(task_id) if not isinstance(task_id, UUID) else task_id
    assert uid in _agent_tasks_db, "precondition: task should hold a live object"
    del _agent_tasks_db[uid]
    assert uid not in _agent_tasks_db


def test_cancel_task_that_lives_on_another_instance():
    payload = {
        "goal": "Cancel test goal",
        "provider": "mock",
        "permissions": ["READ"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    task_id = response.json()["task_id"]

    _drop_local_only(task_id)

    cancel_resp = client.post(f"/api/v1/agent/tasks/{task_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    poll = client.get(f"/api/v1/agent/tasks/{task_id}")
    assert poll.status_code == 200
    assert poll.json()["status"] == "CANCELLED"


def test_approve_task_that_lives_on_another_instance():
    payload = {
        "goal": "Create benchmark requiring approval",
        "provider": "mock",
        "permissions": ["READ", "EXECUTE", "PUBLISH"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    task_id = data["task_id"]
    assert data["status"] == "WAITING_FOR_APPROVAL"
    approval_token = data["approval_token"]
    assert approval_token is not None

    _drop_local_only(task_id)

    appr_resp = client.post(
        f"/api/v1/agent/tasks/{task_id}/approve", json={"approval_token": approval_token}
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] in RESUME_LEAF_STATUSES

    poll = client.get(f"/api/v1/agent/tasks/{task_id}")
    assert poll.status_code == 200
    assert poll.json()["status"] == appr_resp.json()["status"]


def test_clarify_task_that_lives_on_another_instance():
    payload = {
        "goal": "Need clarification test and completed",
        "provider": "mock",
        "permissions": ["READ", "WRITE", "EXECUTE", "PUBLISH"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    task_id = data["task_id"]
    clarify_id = data["clarification_id"]
    assert data["status"] == "WAITING_FOR_CLARIFICATION"

    _drop_local_only(task_id)

    clarify_resp = client.post(
        f"/api/v1/agent/tasks/{task_id}/clarify",
        json={"clarification_id": clarify_id, "answer": "Test addition"},
    )
    assert clarify_resp.status_code == 200
    assert clarify_resp.json()["status"] in RESUME_LEAF_STATUSES

    poll = client.get(f"/api/v1/agent/tasks/{task_id}")
    assert poll.status_code == 200
    assert poll.json()["status"] == clarify_resp.json()["status"]


def test_run_again_from_persisted_source_task():
    payload = {
        "goal": "Need clarification test",
        "provider": "mock",
        "permissions": ["READ", "WRITE", "EXECUTE", "PUBLISH"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    source_id = response.json()["task_id"]

    _drop_local_only(source_id)

    rerun_resp = client.post(f"/api/v1/agent/tasks/{source_id}/run-again")
    assert rerun_resp.status_code == 200
    data = rerun_resp.json()
    assert data["task_id"] != source_id

    poll = client.get(f"/api/v1/agent/tasks/{data['task_id']}")
    assert poll.status_code == 200
    assert poll.json()["task_id"] == data["task_id"]
    assert poll.json()["status"] in RESUME_LEAF_STATUSES


def test_get_task_that_lives_on_another_instance():
    payload = {
        "goal": "Cancel test goal",
        "provider": "mock",
        "permissions": ["READ"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    task_id = response.json()["task_id"]

    _drop_local_only(task_id)

    poll = client.get(f"/api/v1/agent/tasks/{task_id}")
    assert poll.status_code == 200
    assert poll.json()["task_id"] == task_id


def test_list_includes_tasks_parked_on_other_instances():
    payload = {
        "goal": "Cancel test goal",
        "provider": "mock",
        "permissions": ["READ"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    task_id = response.json()["task_id"]

    _drop_local_only(task_id)

    list_resp = client.get("/api/v1/agent/tasks")
    assert list_resp.status_code == 200
    ids = [t["task_id"] for t in list_resp.json()]
    assert task_id in ids


def test_run_agent_task_core_persists_owner_and_heartbeat():
    """The Celery worker entrypoint must claim a PENDING task from the DB
    snapshot, run it, and checkpoint instance_id + heartbeat_at."""
    from uuid import uuid4

    from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus
    from apps.backend.routers.agent import SessionLocal, _agent_tasks_db, _persist_task
    from apps.backend.worker.agent_tasks import run_agent_task_core

    task_id = uuid4()
    task = AgentTask(
        task_id=task_id,
        goal="Cancel test goal",
        status=AgentTaskStatus.PENDING,
        granted_permissions=[AgentPermission.READ],
        primary_provider="mock",
    )

    db = SessionLocal()
    try:
        _persist_task(db, task)
        db.commit()

        run_agent_task_core(
            db,
            str(task_id),
            provider_type="mock",
            model_override=None,
            instance_id="worker-test-instance",
        )

        from atlas_db.models.agent import AgentTaskRecord

        record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
        assert record is not None
        assert record.instance_id == "worker-test-instance"
        assert record.heartbeat_at is not None

        rehydrated = AgentTask.model_validate(record.snapshot)
        # READ-only goal parks at the approval gate rather than executing tools
        assert rehydrated.status == AgentTaskStatus.WAITING_FOR_APPROVAL
    finally:
        assert task_id not in _agent_tasks_db, "worker core must clean up the registry"
        db.close()
