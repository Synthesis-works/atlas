"""P1 Tests: hosted conversational session API.

Run the real sessions router against an in-memory sqlite schema with the DB
session + identity injected (same harness as the P0 agent security tests). The
synchronous mock provider is used where a task loop must actually run; tasks
that would need a real worker are seeded directly.

Security semantics under test: session tasks are server-granted READ only, so
ANY mutation tool (the mock's first planned tool is create_benchmark, WRITE)
parks in WAITING_FOR_APPROVAL. A fresh session therefore lands in
AWAITING_APPROVAL, never READY; the user must explicitly approve each pending
mutation permission.
"""

import uuid
from contextlib import contextmanager

import pytest
from fastapi import status
from fastapi.testclient import TestClient

import atlas_db.models.agent  # noqa: F401  (agent_sessions, agent_task_records)
import atlas_db.models.authoring  # noqa: F401
import atlas_db.models.core  # noqa: F401
import atlas_db.models.dataset  # noqa: F401
import atlas_db.models.execution  # noqa: F401
import atlas_db.models.outbox  # noqa: F401

from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus
from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.agent import AgentSession, AgentTaskRecord

USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
ORG_A = uuid.uuid4()


def _claims(user_id: uuid.UUID, *, org_id: uuid.UUID | None = None) -> TokenClaims:
    return TokenClaims(
        sub=user_id,
        membership_id=uuid.uuid4(),
        organization_id=org_id,
        exp=4_102_444_800,
        iat=1_600_000_000,
        jti=uuid.uuid4(),
    )


@contextmanager
def _session_client(db, identity: TokenClaims):
    app.dependency_overrides.update(
        {
            get_db_session: lambda: db,
            require_authenticated: lambda: identity,
        }
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolate_task_registry():
    from apps.backend.routers.agent import _agent_tasks_db

    _agent_tasks_db.clear()
    yield
    _agent_tasks_db.clear()


def _seed_session(
    db,
    *,
    owner: uuid.UUID,
    org_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    status_value: str = "ACTIVE",
    current_task_id: uuid.UUID | None = None,
    transcript: list | None = None,
    provider: str = "mock",
) -> uuid.UUID:
    session = AgentSession(
        id=uuid.uuid4(),
        created_by_user_id=owner,
        organization_id=org_id,
        title="seeded session",
        project_id=project_id,
        status=status_value,
        current_task_id=current_task_id,
        transcript=list(transcript or []),
        provider=provider,
    )
    db.add(session)
    db.commit()
    return session.id


def _persist_task_row(db, *, task, created_by: uuid.UUID, org_id: uuid.UUID | None = None) -> None:
    db.add(
        AgentTaskRecord(
            task_id=task.task_id,
            goal=task.goal,
            status=task.status.value,
            snapshot=task.model_dump(mode="json"),
            created_by_user_id=created_by,
            organization_id=org_id,
        )
    )
    db.commit()


def _task(status_value: str, *, goal: str = "seeded task") -> AgentTask:
    return AgentTask(
        goal=goal,
        status=AgentTaskStatus(status_value),
        granted_permissions=[AgentPermission.READ],
    )


def test_all_session_endpoints_require_auth(db_session):
    session_id = str(uuid.uuid4())
    app.dependency_overrides[get_db_session] = lambda: db_session
    try:
        client = TestClient(app)
        routes = [
            ("post", "/api/v1/agent/sessions", {"json": {"goal": "x", "provider": "mock"}}),
            ("get", "/api/v1/agent/sessions", {}),
            ("get", f"/api/v1/agent/sessions/{session_id}", {}),
            ("delete", f"/api/v1/agent/sessions/{session_id}", {}),
            (
                "post",
                f"/api/v1/agent/sessions/{session_id}/messages",
                {"json": {"message": "hi"}},
            ),
            (
                "post",
                f"/api/v1/agent/sessions/{session_id}/approve",
                {"json": {"approval_token": "t"}},
            ),
            (
                "post",
                f"/api/v1/agent/sessions/{session_id}/clarify",
                {"json": {"answer": "a"}},
            ),
            ("post", f"/api/v1/agent/sessions/{session_id}/cancel", {}),
        ]
        for method, url, kwargs in routes:
            resp = getattr(client, method)(url, **kwargs)
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"{method.upper()} {url} -> {resp.status_code}"
            )
    finally:
        app.dependency_overrides.clear()


def test_create_session_runs_mock_turn_and_reads_back(db_session):
    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        created = client.post(
            "/api/v1/agent/sessions",
            json={"goal": "Summarize the project backlog", "provider": "mock"},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["current_task_id"] is not None
        assert body["created_at"] is not None
        # READ-only grant + mock's first tool (create_benchmark) = approval park.
        assert body["state"] == "AWAITING_APPROVAL"
        assert body["pending_action"]["action"] == "approve"
        assert body["pending_action"]["tool_name"] == "create_benchmark"
        roles = [m["role"] for m in body["transcript"]]
        assert roles == ["user", "assistant"]
        assert len(body["transcript"]) == 2

        got = client.get(f"/api/v1/agent/sessions/{body['session_id']}")
        assert got.status_code == 200
        assert got.json()["session_id"] == body["session_id"]
        assert got.json()["state"] == "AWAITING_APPROVAL"
        assert len(got.json()["transcript"]) == 2


def test_create_session_grants_minimal_read_permission(db_session):
    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        created = client.post(
            "/api/v1/agent/sessions",
            json={"goal": "hello session", "provider": "mock"},
        )
        assert created.status_code == 201
        task_id = uuid.UUID(created.json()["current_task_id"])

        record = (
            db_session.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
        )
        assert record is not None, "task must be persisted"
        snapshot = AgentTask.model_validate(record.snapshot)
        assert snapshot.created_by_user_id == USER_A
        assert snapshot.organization_id == ORG_A
        assert snapshot.granted_permissions == [AgentPermission.READ]


def test_session_ownership_enforced(db_session):
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A)

    with _session_client(db_session, _claims(USER_B, org_id=ORG_A)) as client:
        assert client.get(f"/api/v1/agent/sessions/{session_id}").status_code == 403
        assert client.delete(f"/api/v1/agent/sessions/{session_id}").status_code == 403
        assert (
            client.post(
                f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "hi"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/agent/sessions/{session_id}/approve", json={"approval_token": "t"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/agent/sessions/{session_id}/clarify", json={"answer": "a"}
            ).status_code
            == 403
        )
        assert client.post(f"/api/v1/agent/sessions/{session_id}/cancel").status_code == 403

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        assert client.get(f"/api/v1/agent/sessions/{session_id}").status_code == 200


def test_unknown_session_returns_404(db_session):
    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        assert client.get(f"/api/v1/agent/sessions/{uuid.uuid4()}").status_code == 404


def test_send_message_starts_new_turn(db_session):
    completed = _task("COMPLETED", goal="First goal")
    _persist_task_row(db_session, task=completed, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(
        db_session,
        owner=USER_A,
        org_id=ORG_A,
        current_task_id=completed.task_id,
        transcript=[
            {
                "role": "user",
                "content": "First goal",
                "task_id": str(completed.task_id),
                "created_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        first_task = client.get(f"/api/v1/agent/sessions/{session_id}").json()["current_task_id"]

        sent = client.post(
            f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "Second goal"}
        )
        assert sent.status_code == 200
        body = sent.json()
        assert body["session"]["current_task_id"] != first_task
        assert body["session"]["current_task_id"] != str(completed.task_id)
        # New READ-only turn parks at approval too.
        assert body["session"]["state"] == "AWAITING_APPROVAL"
        assert body["reply"]
        transcript = [m["content"] for m in body["session"]["transcript"]]
        assert "First goal" in transcript
        assert "Second goal" in transcript


def test_message_while_running_returns_409(db_session):
    task = _task("EXECUTING")
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A, current_task_id=task.task_id)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        resp = client.post(
            f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "interrupt"}
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


def test_message_while_waiting_for_execution_returns_409(db_session):
    task = _task("WAITING_FOR_EXECUTION")
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A, current_task_id=task.task_id)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        resp = client.post(
            f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "nudge"}
        )
        assert resp.status_code == status.HTTP_409_CONFLICT


def test_clarification_flow_via_clarify_endpoint(db_session):
    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        created = client.post(
            "/api/v1/agent/sessions",
            json={"goal": "need clarification on scope", "provider": "mock"},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["state"] == "AWAITING_CLARIFICATION"
        assert body["pending_action"]["action"] == "clarify"
        session_id = body["session_id"]

        answered = client.post(
            f"/api/v1/agent/sessions/{session_id}/clarify", json={"answer": "addition"}
        )
        assert answered.status_code == 200
        answered_body = answered.json()
        assert answered_body["session"]["state"] == "AWAITING_APPROVAL"
        assert answered_body["reply"]


def test_clarification_flow_via_message_turn(db_session):
    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        created = client.post(
            "/api/v1/agent/sessions",
            json={"goal": "please clarify the dataset", "provider": "mock"},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["state"] == "AWAITING_CLARIFICATION"
        session_id = body["session_id"]

        answered = client.post(
            f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "use subtraction"}
        )
        assert answered.status_code == 200
        answered_body = answered.json()
        assert answered_body["session"]["state"] == "AWAITING_APPROVAL"
        assert answered_body["reply"]


def test_approval_flow_with_wrong_and_right_token(db_session):
    goal = "approval workflow"
    task = _task("WAITING_FOR_APPROVAL", goal=goal)
    task.pending_tool_call = {"tool_name": "create_benchmark", "arguments": {"name": "x"}}
    task.approval_token = "tok-123"
    task.primary_provider = "mock"
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A, current_task_id=task.task_id)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        resp_401 = client.post(
            f"/api/v1/agent/sessions/{session_id}/approve", json={"approval_token": "wrong"}
        )
        assert resp_401.status_code == status.HTTP_401_UNAUTHORIZED

        ok = client.post(
            f"/api/v1/agent/sessions/{session_id}/approve", json={"approval_token": "tok-123"}
        )
        assert ok.status_code == 200
        ok_body = ok.json()
        # create_benchmark (WRITE) is granted and the task resumes; the next mock
        # step (run_benchmark, EXECUTE) parks again.
        assert ok_body["session"]["state"] == "AWAITING_APPROVAL"
        assert ok_body["reply"]

        record = (
            db_session.query(AgentTaskRecord)
            .filter(AgentTaskRecord.task_id == task.task_id)
            .first()
        )
        snapshot = AgentTask.model_validate(record.snapshot)
        assert AgentPermission.WRITE in snapshot.granted_permissions


def test_cancel_running_session(db_session):
    task = _task("EXECUTING")
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A, current_task_id=task.task_id)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        resp = client.post(f"/api/v1/agent/sessions/{session_id}/cancel")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session"]["state"] == "READY"
        assert "cancelled" in body["reply"].lower()


def test_delete_archives_and_hides_session(db_session):
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        deleted = client.delete(f"/api/v1/agent/sessions/{session_id}")
        assert deleted.status_code == 200

        listed = client.get("/api/v1/agent/sessions")
        assert listed.json() == []

        got = client.get(f"/api/v1/agent/sessions/{session_id}")
        assert got.status_code == 200
        assert got.json()["status"] == "ARCHIVED"


def test_archived_session_cannot_continue_receiving_turns(db_session):
    task = _task("WAITING_FOR_APPROVAL", goal="archived")
    task.pending_tool_call = {"tool_name": "create_benchmark", "arguments": {"name": "x"}}
    task.approval_token = "tok-123"
    task.primary_provider = "mock"
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A, current_task_id=task.task_id)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        assert client.delete(f"/api/v1/agent/sessions/{session_id}").status_code == 200
        assert (
            client.post(
                f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "revive"}
            ).status_code
            == status.HTTP_409_CONFLICT
        )
        assert (
            client.post(
                f"/api/v1/agent/sessions/{session_id}/approve", json={"approval_token": "tok-123"}
            ).status_code
            == status.HTTP_409_CONFLICT
        )
        assert (
            client.post(
                f"/api/v1/agent/sessions/{session_id}/clarify", json={"answer": "a"}
            ).status_code
            == status.HTTP_409_CONFLICT
        )
        assert client.post(f"/api/v1/agent/sessions/{session_id}/cancel").status_code == 200
        assert client.get(f"/api/v1/agent/sessions/{session_id}").json()["status"] == "ARCHIVED"
        assert client.get("/api/v1/agent/sessions").json() == []


def test_transcript_is_bounded(db_session):
    long_transcript = [
        {
            "role": "user",
            "content": f"message {i}",
            "task_id": str(uuid.uuid4()),
            "created_at": "2026-01-01T00:00:00Z",
        }
        for i in range(40)
    ]
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A, transcript=long_transcript)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        sent = client.post(
            f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "new turn"}
        )
        assert sent.status_code == 200
        assert len(sent.json()["session"]["transcript"]) <= 30


def test_session_list_is_owner_scoped(db_session):
    a = _seed_session(db_session, owner=USER_A, org_id=ORG_A)
    b = _seed_session(db_session, owner=USER_B, org_id=ORG_A)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        listed = client.get("/api/v1/agent/sessions")
        assert [s["session_id"] for s in listed.json()] == [str(a)]

    with _session_client(db_session, _claims(USER_B, org_id=ORG_A)) as client:
        listed = client.get("/api/v1/agent/sessions")
        assert [s["session_id"] for s in listed.json()] == [str(b)]


def test_task_create_rate_limit_on_session_create(db_session, monkeypatch):
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "agent_rate_limit_max_tasks_per_day", 1)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        first = client.post("/api/v1/agent/sessions", json={"goal": "one", "provider": "mock"})
        assert first.status_code == 201

        second = client.post("/api/v1/agent/sessions", json={"goal": "two", "provider": "mock"})
        assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert second.headers.get("Retry-After")
        assert second.json()["error"]["code"] == "HTTP_429"


def test_minute_rate_limit_on_session_list(db_session, monkeypatch):
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "agent_rate_limit_max_per_minute", 1)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        first = client.get("/api/v1/agent/sessions")
        assert first.status_code == 200

        second = client.get("/api/v1/agent/sessions")
        assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert second.json()["error"]["code"] == "HTTP_429"
