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

from tests._agent_auth import AuthenticatedTestClient


@pytest.fixture(autouse=True)
def setup_db():
    from atlas_db.core.engine import engine

    if "sqlite" in str(engine.url):
        from atlas_db.core.initialize import initialize_database_schema

        initialize_database_schema(engine)
    from apps.backend.routers.agent import _agent_tasks_db

    _agent_tasks_db.clear()


from apps.backend.main import app  # noqa: E402

client = AuthenticatedTestClient(app, user_id="33333333-3333-4333-8333-333333333333")

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


def test_clarify_persists_planning_before_outbox_dispatch(monkeypatch):
    """With AGENT_TASKS_CELERY_EXECUTION=true the /agent/tasks clarify
    transition must be durable BEFORE the outbox run is enqueued. The worker
    re-reads the persisted snapshot in its own process; a stale
    WAITING_FOR_CLARIFICATION row (pre-fix ordering) is not claimable, so the
    resumed run no-ops and the user's answer is stranded."""
    from uuid import UUID

    from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus
    from apps.backend.config import settings
    from apps.backend.routers.agent import SessionLocal, _persist_task
    from apps.backend.worker.agent_tasks import run_agent_task_core
    from atlas_db.models.agent import AgentTaskRecord
    from atlas_db.models.outbox import OutboxMessage

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    task = AgentTask(
        goal="Need clarification before proceeding",
        status=AgentTaskStatus.WAITING_FOR_CLARIFICATION,
        granted_permissions=[AgentPermission.READ],
        primary_provider="gemini",
        created_by_user_id=UUID("33333333-3333-4333-8333-333333333333"),
        clarification_prompt="Should we test addition or subtraction?",
        clarification_request="Should we test addition or subtraction?",
        clarification_id="clarify_abc123",
    )

    db = SessionLocal()
    try:
        _persist_task(db, task)

        resp = client.post(
            f"/api/v1/agent/tasks/{task.task_id}/clarify",
            json={"clarification_id": "clarify_abc123", "answer": "addition"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PLANNING"

        db.expire_all()
        record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task.task_id).first()
        snapshot = AgentTask.model_validate(record.snapshot)
        assert snapshot.status == AgentTaskStatus.PLANNING
        assert snapshot.clarification_request is None
        assert [c["answer"] for c in snapshot.past_clarifications] == ["addition"]

        queued = (
            db.query(OutboxMessage)
            .filter(OutboxMessage.event_type == "AgentRunRequestedEvent")
            .filter(OutboxMessage.aggregate_id == task.task_id)
            .first()
        )
        assert queued is not None, "the resumed run must be enqueued via the outbox"

        # Simulate the worker re-reading the row in a fresh process. A stale
        # WAITING_FOR_CLARIFICATION snapshot is not claimable -> skips the run.
        resumed = run_agent_task_core(
            db,
            task.task_id,
            provider_type="mock",
            model_override=None,
            instance_id="worker-test-instance",
        )
        assert resumed == "WAITING_FOR_APPROVAL"
        db.expire_all()
        record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task.task_id).first()
        assert (
            AgentTask.model_validate(record.snapshot).status == AgentTaskStatus.WAITING_FOR_APPROVAL
        )
    finally:
        db.close()


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


def test_dispatch_writes_outbox_when_celery_enabled(monkeypatch):
    """With AGENT_TASKS_CELERY_EXECUTION=true the router must NOT enqueue to
    Redis directly (the serverless API has no broker); it persists an
    ``AgentRunRequestedEvent`` transactional-outbox row for the worker sweep."""
    from unittest.mock import Mock

    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    from apps.backend.routers.agent import SessionLocal, _enqueue_agent_run
    from apps.backend.worker import agent_tasks

    chain = Mock()
    monkeypatch.setattr(agent_tasks.run_agent_task, "delay", chain.delay)

    payload = {
        "goal": "Trolley problem benchmark",
        "provider": "gemini",
        "permissions": ["READ", "WRITE", "EXECUTE", "PUBLISH"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    assert response.json()["primary_provider"] == "gemini"

    chain.delay.assert_not_called(), "serverless dispatch must not call .delay()"

    from uuid import UUID

    from atlas_db.models.outbox import OutboxMessage
    from packages.execution_engine.domain.events import AgentRunRequestedEvent

    db = SessionLocal()
    try:
        row = (
            db.query(OutboxMessage)
            .filter(OutboxMessage.event_type == "AgentRunRequestedEvent")
            .order_by(OutboxMessage.created_at.desc())
            .first()
        )
        assert row is not None, "expected an AgentRunRequestedEvent outbox row"
        assert row.aggregate_id == UUID(response.json()["task_id"])
        assert row.aggregate_type == "AgentTask"
        assert row.payload["provider_type"] == "gemini"
        assert "task_id" in row.payload
    finally:
        db.close()

    # Guard against regressing to a direct broker enqueue replacement.
    assert _enqueue_agent_run.__name__ == "_enqueue_agent_run"
    assert AgentRunRequestedEvent.__name__ == "AgentRunRequestedEvent"


def test_agent_run_subscriber_enqueues_on_worker_side(monkeypatch):
    """The outbox sweep subscriber must forward AgentRunRequestedEvent to the
    local run_agent_task Celery task (executed on the worker's broker)."""
    from datetime import UTC, datetime
    from unittest.mock import Mock
    from uuid import uuid4

    from apps.backend.worker.agent_tasks import AgentRunSubscriber, run_agent_task
    from packages.execution_engine.application.outbox_dispatcher import OutboxDispatcher
    from packages.execution_engine.domain.events import AgentRunRequestedEvent

    task_id = uuid4()
    event = AgentRunRequestedEvent(
        timestamp=datetime.now(UTC),
        task_id=task_id,
        provider_type="groq",
        model_override="llama-3.3-70b-versatile",
    )

    # Registry round-trip: an outbox message must deserialize to the event.
    deserialized = OutboxDispatcher(session=None, publisher=None)._deserialize_event(
        "AgentRunRequestedEvent", event.to_dict(), event.timestamp
    )
    assert deserialized.task_id == task_id
    assert deserialized.provider_type == "groq"

    chain = Mock()
    monkeypatch.setattr(run_agent_task, "delay", chain.delay)

    AgentRunSubscriber().handle(event)
    chain.delay.assert_called_once_with(str(task_id), "groq", "llama-3.3-70b-versatile")


def test_get_and_list_reflect_worker_side_state_change():
    """A read on the *same* instance must not return a stale in-memory copy.

    The worker parks/runs tasks in another process and checkpoints every state
    transition to the DB; the creating lambda's ``_agent_tasks_db`` working
    copy stays frozen (e.g. PENDING) for the lifetime of that warm instance.
    GET /tasks/{id} and GET /tasks must converge on the persisted snapshot.
    """
    payload = {
        "goal": "Stale copy test",
        "provider": "mock",
        "permissions": ["READ"],
    }
    response = client.post("/api/v1/agent/tasks", json=payload)
    assert response.status_code == 201
    task_id = response.json()["task_id"]

    from atlas_db.models.agent import AgentTaskRecord
    from apps.backend.routers.agent import SessionLocal

    db = SessionLocal()
    try:
        record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
        assert record is not None
        snap = dict(record.snapshot)
        snap["status"] = "CANCELLED"
        record.status = "CANCELLED"
        record.snapshot = snap
        db.commit()
    finally:
        db.close()

    got = client.get(f"/api/v1/agent/tasks/{task_id}")
    assert got.status_code == 200
    assert got.json()["status"] == "CANCELLED"

    listed = client.get("/api/v1/agent/tasks")
    assert listed.status_code == 200
    assert any(t["task_id"] == task_id and t["status"] == "CANCELLED" for t in listed.json())
