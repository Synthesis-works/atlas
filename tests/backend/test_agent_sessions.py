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

import json
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
from atlas_db.models.outbox import OutboxMessage

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


def _pending_clarification_task() -> AgentTask:
    """A WAITING_FOR_CLARIFICATION task on a non-mock provider, seeded directly
    (the mock provider would never park; it answers or resumes inline)."""
    task = _task("WAITING_FOR_CLARIFICATION", goal="need clarification on scope")
    task.primary_provider = "gemini"
    task.clarification_prompt = "Should we test addition or subtraction?"
    task.clarification_request = "Should we test addition or subtraction?"
    task.clarification_id = "clarify_seeded01"
    return task


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


def _assert_clarify_persisted_before_dispatch(db_session, task: AgentTask, answer: str) -> None:
    """The persisted snapshot must already be PLANNING with the answer BEFORE
    the worker (fresh process, re-reading the row) claims the run."""
    from apps.backend.worker.agent_tasks import run_agent_task_core

    record = (
        db_session.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task.task_id).first()
    )
    assert record is not None
    snapshot = AgentTask.model_validate(record.snapshot)
    assert snapshot.status == AgentTaskStatus.PLANNING
    assert snapshot.clarification_request is None
    assert snapshot.clarification_prompt is None
    assert [c["answer"] for c in snapshot.past_clarifications] == [answer]

    queued = (
        db_session.query(OutboxMessage)
        .filter(OutboxMessage.event_type == "AgentRunRequestedEvent")
        .filter(OutboxMessage.aggregate_id == task.task_id)
        .first()
    )
    assert queued is not None, "the resumed run must be enqueued via the outbox"

    # Simulate the worker's fresh-process re-read. A stale row (pre-fix) is not
    # claimable, so run_agent_task_core no-ops and the answer is stranded.
    resumed = run_agent_task_core(
        db_session, task.task_id, provider_type="mock", model_override=None
    )
    assert resumed == "WAITING_FOR_APPROVAL"
    record = (
        db_session.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task.task_id).first()
    )
    assert AgentTask.model_validate(record.snapshot).status == AgentTaskStatus.WAITING_FOR_APPROVAL


def test_clarify_persists_planning_before_outbox_dispatch(db_session, monkeypatch):
    """With AGENT_TASKS_CELERY_EXECUTION=true the /clarify transition must be
    durable before the outbox run is enqueued. The worker re-reads the
    persisted snapshot in its own process, so a WAITING_FOR_CLARIFICATION row
    (pre-fix ordering: no persist in the dispatch path) makes the resumed run
    unclaimable and loses the user's answer."""
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    task = _pending_clarification_task()
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(
        db_session,
        owner=USER_A,
        org_id=ORG_A,
        current_task_id=task.task_id,
        provider="gemini",
    )

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        resp = client.post(
            f"/api/v1/agent/sessions/{session_id}/clarify", json={"answer": "addition"}
        )
        assert resp.status_code == 200

    db_session.expire_all()
    _assert_clarify_persisted_before_dispatch(db_session, task, "addition")


def test_message_clarification_persists_planning_before_outbox_dispatch(db_session, monkeypatch):
    """Same durability boundary as the /clarify path, exercised through a
    message turn while the task sits in WAITING_FOR_CLARIFICATION."""
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    task = _pending_clarification_task()
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(
        db_session,
        owner=USER_A,
        org_id=ORG_A,
        current_task_id=task.task_id,
        provider="gemini",
    )

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        resp = client.post(
            f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "addition"}
        )
        assert resp.status_code == 200

    db_session.expire_all()
    _assert_clarify_persisted_before_dispatch(db_session, task, "addition")


def test_approval_flow_with_wrong_and_right_token(db_session):
    goal = "approval workflow"
    task = _task("WAITING_FOR_APPROVAL", goal=goal)
    task.pending_tool_call = {"tool_name": "create_benchmark", "arguments": {"name": "x"}}
    task.approval_token = "tok-123"
    task.primary_provider = "mock"
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A, current_task_id=task.task_id)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        fetched = client.get(f"/api/v1/agent/sessions/{session_id}").json()
        pending = fetched["pending_action"]
        assert pending["action"] == "approve"
        assert pending["tool_name"] == "create_benchmark"
        assert pending["approval_token"] == "tok-123"

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


# ---------------------------------------------------------------------------
# 0.2.3 model-default regressions: an omitted session model must resolve to the
# selected provider's OWN configured default, never the generic
# "gemini-3.5-flash-lite" literal.
# ---------------------------------------------------------------------------


def _snapshot_for(db, task_id) -> AgentTask:
    record = db.query(AgentTaskRecord).filter(AgentTaskRecord.task_id == task_id).first()
    assert record is not None, "task must be persisted"
    return AgentTask.model_validate(record.snapshot)


def _latest_run_request(db, task_id) -> dict | None:
    queued = (
        db.query(OutboxMessage)
        .filter(OutboxMessage.event_type == "AgentRunRequestedEvent")
        .filter(OutboxMessage.aggregate_id == task_id)
        .order_by(OutboxMessage.created_at.desc())
        .first()
    )
    return queued.payload if queued is not None else None


@pytest.mark.parametrize(
    ("provider", "expected_default"),
    [
        ("groq", "openai/gpt-oss-20b"),
        ("gemini", "gemini-3.5-flash-lite"),
        ("mistral", "mistral-small-latest"),
    ],
)
def test_omitted_session_model_dispatches_provider_default_not_gemini(
    db_session, monkeypatch, provider, expected_default
):
    """The 0.2.2 production bug: provider=groq + omitted model dispatched the
    generic 'gemini-3.5-flash-lite' literal and Groq returned 404 model_not_found.
    An omitted model must stay None on the task and outbox, and the provider
    factory must resolve the provider's own default."""
    from apps.backend.agent.providers.router import build_provider_instance
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        created = client.post(
            "/api/v1/agent/sessions",
            json={"goal": f"regression omitted model {provider}", "provider": provider},
        )
        assert created.status_code == 201
        task_id = uuid.UUID(created.json()["current_task_id"])

    task = _snapshot_for(db_session, task_id)
    assert task.primary_provider == provider
    assert task.model is None, "omitted model must stay None on the task snapshot"

    payload = _latest_run_request(db_session, task_id)
    assert payload is not None
    assert payload.get("model_override") is None

    if provider in ("groq", "mistral"):
        assert "gemini-3.5-flash-lite" not in json.dumps(payload)

    provider_instance = build_provider_instance(provider, payload.get("model_override"))
    assert provider_instance is not None
    assert provider_instance.model == expected_default


def test_omitted_model_explicitly_groq_resolves_to_gpt_oss(db_session, monkeypatch):
    """IMPORTANT 0.2.3 regression: provider=groq, model omitted must NEVER yield
    model_override='gemini-3.5-flash-lite'; the resolved model must be groq's
    own default (openai/gpt-oss-20b)."""
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        created = client.post(
            "/api/v1/agent/sessions",
            json={"goal": "groq omitted model must default to gpt-oss-20b", "provider": "groq"},
        )
        assert created.status_code == 201
        task_id = uuid.UUID(created.json()["current_task_id"])

    payload = _latest_run_request(db_session, task_id)
    assert payload is not None
    assert payload["model_override"] is None

    from apps.backend.agent.providers.router import build_provider_instance

    resolved = build_provider_instance("groq", payload["model_override"])
    assert resolved is not None
    assert resolved.model == "openai/gpt-oss-20b"
    assert resolved.model != "gemini-3.5-flash-lite"


def test_explicit_session_model_is_preserved(db_session, monkeypatch):
    """An explicitly-chosen model is honored end-to-end: task snapshot, outbox
    event, persisted session row, and the built provider instance."""
    from apps.backend.agent.providers.router import build_provider_instance
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    explicit = "llama-3.3-70b-versatile"
    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        created = client.post(
            "/api/v1/agent/sessions",
            json={"goal": "explicit model preserved", "provider": "groq", "model": explicit},
        )
        assert created.status_code == 201
        task_id = uuid.UUID(created.json()["current_task_id"])

    task = _snapshot_for(db_session, task_id)
    assert task.model == explicit

    payload = _latest_run_request(db_session, task_id)
    assert payload is not None
    assert payload["model_override"] == explicit

    session_row = (
        db_session.query(AgentSession)
        .filter(AgentSession.id == uuid.UUID(created.json()["session_id"]))
        .first()
    )
    assert session_row is not None
    assert session_row.model == explicit

    provider_instance = build_provider_instance("groq", task.model)
    assert provider_instance is not None
    assert provider_instance.model == explicit


def test_approval_redispatch_keeps_omitted_model_none(db_session, monkeypatch):
    """Re-dispatching a parked session task after approval must keep
    model_override=None, not resurrect the gemini default."""
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    task = _task("WAITING_FOR_APPROVAL", goal="approval model regression")
    task.primary_provider = "groq"
    task.pending_tool_call = {"tool_name": "create_benchmark", "arguments": {"name": "x"}}
    task.approval_token = "tok-model"
    _persist_task_row(db_session, task=task, created_by=USER_A, org_id=ORG_A)
    session_id = _seed_session(
        db_session, owner=USER_A, org_id=ORG_A, current_task_id=task.task_id, provider="groq"
    )

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        ok = client.post(
            f"/api/v1/agent/sessions/{session_id}/approve", json={"approval_token": "tok-model"}
        )
        assert ok.status_code == 200

    payload = _latest_run_request(db_session, task.task_id)
    assert payload is not None
    assert payload["model_override"] is None
    assert "gemini-3.5-flash-lite" not in json.dumps(payload)


def test_new_message_turn_omitted_model_keeps_provider_default(db_session, monkeypatch):
    """A follow-up session message spawns a new task that still dispatches with
    model_override=None when the session carries no explicit model."""
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_tasks_celery_execution", True)

    session_id = _seed_session(db_session, owner=USER_A, org_id=ORG_A, provider="groq")

    with _session_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        sent = client.post(
            f"/api/v1/agent/sessions/{session_id}/messages", json={"message": "next turn"}
        )
        assert sent.status_code == 200
        task_id = uuid.UUID(sent.json()["session"]["current_task_id"])

    payload = _latest_run_request(db_session, task_id)
    assert payload is not None
    assert payload["provider_type"] == "groq"
    assert payload["model_override"] is None
    assert "gemini-3.5-flash-lite" not in json.dumps(payload)
