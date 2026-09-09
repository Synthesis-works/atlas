"""P0 security-boundary tests for the Atlas Agent API.

Every ``/api/v1/agent/*`` endpoint must require a valid Bearer JWT, and task /
report access must be scoped to the authenticated owner, with opt-in per-user
rate limiting (disabled by default). These tests run the real router against an
in-memory sqlite schema with the DB session, identity, and (for reports)
project-authorization service injected, so the HTTP boundary itself is
exercised end-to-end without any provider/execution backend.

The synchronous mock agent loop is deliberately NOT driven here (it parks at
WAITING_FOR_EXECUTION without a live worker stack and stalls on Redis/Ollama
connection retries); task rows are seeded directly, and task dispatch is
neutralized for the one create-path test.
"""

import uuid
from contextlib import contextmanager

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

import atlas_db.models.agent  # noqa: F401  (agent_task_records, api_usage_counters)
import atlas_db.models.authoring  # noqa: F401
import atlas_db.models.core  # noqa: F401  (noqa: F401)
import atlas_db.models.dataset  # noqa: F401
import atlas_db.models.execution  # noqa: F401
import atlas_db.models.leaderboard  # noqa: F401
import atlas_db.models.outbox  # noqa: F401
import atlas_db.models.reporting  # noqa: F401

from apps.backend.authz import get_project_authz_service
from apps.backend.dependencies import get_db_session, require_authenticated
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims


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
def _agent_client(db, identity: TokenClaims, *, authz=None):
    """TestClient over the real app with identity + db session injected."""
    overrides = {
        get_db_session: lambda: db,
        require_authenticated: lambda: identity,
    }
    if authz is not None:
        overrides[get_project_authz_service] = lambda: authz
    app.dependency_overrides.update(overrides)
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


def _seed_task(
    db,
    *,
    created_by: uuid.UUID | None,
    owner_org: uuid.UUID | None = None,
    status_value: str = "PENDING",
    goal: str = "Seeded agent task",
) -> uuid.UUID:
    """Insert an AgentTaskRecord directly, bypassing the agent loop."""
    from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus

    task = AgentTask(
        goal=goal,
        status=AgentTaskStatus(status_value),
        granted_permissions=[
            AgentPermission.READ,
            AgentPermission.WRITE,
            AgentPermission.EXECUTE,
            AgentPermission.PUBLISH,
        ],
    )
    if created_by is not None:
        task.created_by_user_id = created_by
        task.organization_id = owner_org

    from atlas_db.models.agent import AgentTaskRecord

    db.add(
        AgentTaskRecord(
            task_id=task.task_id,
            goal=task.goal,
            status=task.status.value,
            snapshot=task.model_dump(mode="json"),
            created_by_user_id=created_by,
            organization_id=owner_org,
        )
    )
    db.commit()
    return task.task_id


USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
ORG_A = uuid.uuid4()


def test_all_agent_endpoints_require_auth(db_session):
    """No endpoint may be reachable without a Bearer token."""
    tid = str(uuid.uuid4())
    app.dependency_overrides[get_db_session] = lambda: db_session
    try:
        client = TestClient(app)
        routes = [
            ("post", "/api/v1/agent/tasks", {"json": {"goal": "x", "provider": "mock"}}),
            ("get", f"/api/v1/agent/tasks/{tid}", {}),
            ("get", f"/api/v1/agent/reports/{tid}", {}),
            ("get", "/api/v1/agent/tasks", {}),
            ("delete", "/api/v1/agent/tasks", {}),
            ("delete", f"/api/v1/agent/tasks/{tid}", {}),
            ("post", f"/api/v1/agent/tasks/{tid}/approve", {"json": {"approval_token": "t"}}),
            ("post", f"/api/v1/agent/tasks/{tid}/cancel", {}),
            ("post", f"/api/v1/agent/tasks/{tid}/clarify", {"json": {"answer": "a"}}),
            ("post", f"/api/v1/agent/tasks/{tid}/run-again", {}),
            ("get", "/api/v1/agent/tools", {}),
            ("get", "/api/v1/agent/providers", {}),
        ]
        for method, url, kwargs in routes:
            resp = getattr(client, method)(url, **kwargs)
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"{method.upper()} {url} -> {resp.status_code}"
            )
    finally:
        app.dependency_overrides.clear()


def test_authenticated_user_can_create_and_read_own_task(db_session, monkeypatch):
    """The happy path: an authenticated caller can create (dispatch), read and
    list their own task."""

    def _noop_dispatch(background_tasks, db, task_id, provider_type, model_override):
        return None

    identity = _claims(USER_A, org_id=ORG_A)
    with _agent_client(db_session, identity) as client:
        monkeypatch.setattr("apps.backend.routers.agent._dispatch_agent_run", _noop_dispatch)
        resp = client.post(
            "/api/v1/agent/tasks",
            json={"goal": "authenticated create", "provider": "gemini"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        task_id = resp.json()["task_id"]

        got = client.get(f"/api/v1/agent/tasks/{task_id}")
        assert got.status_code == 200
        assert got.json()["task_id"] == task_id
        assert got.json()["goal"] == "authenticated create"

        listed = client.get("/api/v1/agent/tasks")
        assert listed.status_code == 200
        assert [t["task_id"] for t in listed.json()] == [task_id]


def test_cross_user_access_denied_on_all_mutations(db_session):
    task_id = _seed_task(db_session, created_by=USER_A, owner_org=ORG_A)

    with _agent_client(db_session, _claims(USER_B, org_id=ORG_A)) as client:
        assert client.get(f"/api/v1/agent/tasks/{task_id}").status_code == 403
        assert client.delete(f"/api/v1/agent/tasks/{task_id}").status_code == 403
        assert (
            client.post(
                f"/api/v1/agent/tasks/{task_id}/approve",
                json={"approval_token": "t"},
            ).status_code
            == 403
        )
        assert client.post(f"/api/v1/agent/tasks/{task_id}/cancel").status_code == 403
        assert (
            client.post(
                f"/api/v1/agent/tasks/{task_id}/clarify",
                json={"answer": "a"},
            ).status_code
            == 403
        )
        assert client.post(f"/api/v1/agent/tasks/{task_id}/run-again").status_code == 403

    # The owner is unaffected by all those denials.
    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        assert client.get(f"/api/v1/agent/tasks/{task_id}").status_code == 200


def test_list_and_clear_are_owner_scoped(db_session):
    task_a = _seed_task(db_session, created_by=USER_A, owner_org=ORG_A)
    task_b = _seed_task(db_session, created_by=USER_B, owner_org=ORG_A)

    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        listed = client.get("/api/v1/agent/tasks")
        assert [t["task_id"] for t in listed.json()] == [str(task_a)]

        clear = client.delete("/api/v1/agent/tasks")
        assert clear.status_code == 200
        assert client.get("/api/v1/agent/tasks").json() == []

    # User B's task survives user A's clear, and stays visible to B.
    with _agent_client(db_session, _claims(USER_B, org_id=ORG_A)) as client:
        assert client.get(f"/api/v1/agent/tasks/{task_b}").status_code == 200
        assert [t["task_id"] for t in client.get("/api/v1/agent/tasks").json()] == [str(task_b)]


def test_legacy_ownerless_tasks_are_hidden(db_session):
    legacy_id = _seed_task(db_session, created_by=None)

    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        got = client.get(f"/api/v1/agent/tasks/{legacy_id}")
        assert got.status_code == 403

        listed = client.get("/api/v1/agent/tasks")
        assert listed.json() == []

        deleted = client.delete(f"/api/v1/agent/tasks/{legacy_id}")
        assert deleted.status_code == 403


def test_run_again_clones_ownership(db_session, monkeypatch):
    def _noop_dispatch(background_tasks, db, task_id, provider_type, model_override):
        return None

    task_a = _seed_task(db_session, created_by=USER_A, owner_org=ORG_A)

    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        monkeypatch.setattr("apps.backend.routers.agent._dispatch_agent_run", _noop_dispatch)
        rerun = client.post(f"/api/v1/agent/tasks/{task_a}/run-again")
        assert rerun.status_code == 200
        clone_id = rerun.json()["task_id"]
        assert clone_id != str(task_a)

    # The clone belongs to A: B cannot touch it, A can read it.
    with _agent_client(db_session, _claims(USER_B, org_id=ORG_A)) as client:
        assert client.get(f"/api/v1/agent/tasks/{clone_id}").status_code == 403
    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        assert client.get(f"/api/v1/agent/tasks/{clone_id}").status_code == 200


class _FakeProjectAuthz:
    """Records the resolved project and honors a configured allow/deny."""

    def __init__(self, allow: bool) -> None:
        self.allow = allow
        self.project_id = None

    def authorize_project_access(self, project_id, user_id, allowed_roles):
        self.project_id = project_id
        if not self.allow:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="denied")


def _seed_report_lineage(db, *, with_execution: bool) -> uuid.UUID:
    from atlas_db.models.core import Project
    from atlas_db.models.execution import Execution, ExecutionStatus
    from atlas_db.models.reporting import Report, ReportVersion

    project = Project(
        org_id=ORG_A, name="P0 security project", slug=f"p0-sec-{uuid.uuid4().hex[:8]}"
    )
    db.add(project)
    db.flush()

    execution_id = None
    if with_execution:
        execution = Execution(
            project_id=project.id,
            benchmark_version_id=uuid.uuid4(),
            target_model="provider/mock",
            status=ExecutionStatus.COMPLETED,
            submitted_by_id=USER_A,
        )
        db.add(execution)
        db.flush()
        execution_id = execution.id

    report = Report(project_id=project.id, name="Agent security report")
    db.add(report)
    db.flush()

    version = ReportVersion(
        report_id=report.id,
        version_string="1.0.0",
        summary="summary",
        execution_id=execution_id,
        created_by_id=USER_A,
    )
    db.add(version)
    db.commit()
    return version.id


def test_report_access_resolves_project_and_authorizes(db_session):
    version_id = _seed_report_lineage(db_session, with_execution=True)
    authz = _FakeProjectAuthz(allow=True)

    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A), authz=authz) as client:
        resp = client.get(f"/api/v1/agent/reports/{version_id}")
        assert resp.status_code == 200
        assert authz.project_id is not None, "authorization must resolve the owning project"

    denying = _FakeProjectAuthz(allow=False)
    with _agent_client(db_session, _claims(USER_B, org_id=ORG_A), authz=denying) as client:
        resp = client.get(f"/api/v1/agent/reports/{version_id}")
        assert resp.status_code == 403


def test_report_without_resolvable_lineage_is_denied(db_session):
    """A report version whose execution lineage cannot be resolved must never
    be reachable through the agent endpoint."""
    version_id = _seed_report_lineage(db_session, with_execution=False)
    authz = _FakeProjectAuthz(allow=True)

    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A), authz=authz) as client:
        resp = client.get(f"/api/v1/agent/reports/{version_id}")
        assert resp.status_code == 403
        assert authz.project_id is None, "authz must not even be consulted"


def test_minute_rate_limit_returns_429_with_retry_after(db_session, monkeypatch):
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "agent_rate_limit_max_per_minute", 1)

    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        first = client.get("/api/v1/agent/tasks")
        assert first.status_code == 200

        second = client.get("/api/v1/agent/tasks")
        assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        retry_after = int(second.headers["Retry-After"])
        assert retry_after >= 1
        body = second.json()
        assert body["error"]["code"] == "HTTP_429"
        assert "Retry after" in body["error"]["message"]


def test_task_create_rate_limit_returns_429(db_session, monkeypatch):
    from apps.backend.config import settings

    monkeypatch.setattr(settings, "agent_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "agent_rate_limit_max_tasks_per_day", 1)

    def _noop_dispatch(background_tasks, db, task_id, provider_type, model_override):
        return None

    monkeypatch.setattr("apps.backend.routers.agent._dispatch_agent_run", _noop_dispatch)

    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        first = client.post(
            "/api/v1/agent/tasks",
            json={"goal": "rate limited create", "provider": "gemini"},
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/agent/tasks",
            json={"goal": "rate limited create 2", "provider": "gemini"},
        )
        assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert second.headers.get("Retry-After")
        assert second.json()["error"]["code"] == "HTTP_429"


def test_rate_limit_does_not_apply_when_disabled(db_session, monkeypatch):
    """agent_rate_limit_enabled defaults to False: unlimited, deterministic."""

    with _agent_client(db_session, _claims(USER_A, org_id=ORG_A)) as client:
        for _ in range(5):
            resp = client.get("/api/v1/agent/tasks")
            assert resp.status_code == 200
