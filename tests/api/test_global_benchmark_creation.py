"""
Regression tests for global benchmark creation (Finding 3).

POST /api/v1/benchmarks must not silently attach to an arbitrary project and
must not create cross-project records without authorization. The target
project_id is now required and enforced through the same project authorization
contract as the project-scoped create endpoint.
"""

import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.benchmarks import BenchmarkRead
from apps.backend.dependencies import require_authenticated
from apps.backend.routers.benchmarks import get_project_authz_service, get_benchmark_app_service

client = TestClient(app)


class FakeAuthz:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail  # (status_code, detail) or None for success

    def authorize_project_access(self, project_id, user_id, allowed_roles):
        self.calls.append({"project_id": project_id, "user_id": user_id, "roles": allowed_roles})
        if self.fail:
            code, detail = self.fail
            raise HTTPException(status_code=code, detail=detail)
        return {"project_id": project_id}


@pytest.fixture
def global_create_env():
    user_id = uuid.uuid4()
    mock_claims = TokenClaims(
        sub=user_id,
        exp=0,
        iat=0,
        jti=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
    )
    project_id = uuid.uuid4()
    called = []

    def mock_create_benchmark(**kwargs):
        called.append(kwargs)
        return BenchmarkRead(
            id=uuid.uuid4(),
            project_id=kwargs["project_id"],
            state="ACTIVE",
            name=kwargs["data"].name,
        )

    fake_authz = FakeAuthz()
    mock_service = type(
        "Service", (), {"create_benchmark": staticmethod(mock_create_benchmark)}
    )()

    app.dependency_overrides[require_authenticated] = lambda: mock_claims
    app.dependency_overrides[get_project_authz_service] = lambda: fake_authz
    app.dependency_overrides[get_benchmark_app_service] = lambda: mock_service

    yield {
        "user_id": user_id,
        "project_id": project_id,
        "authz": fake_authz,
        "calls": called,
    }

    app.dependency_overrides.pop(require_authenticated, None)
    app.dependency_overrides.pop(get_project_authz_service, None)
    app.dependency_overrides.pop(get_benchmark_app_service, None)


def test_global_create_requires_explicit_project_id(global_create_env):
    """Without project_id the request is rejected; no first-project fallback."""
    res = client.post("/api/v1/benchmarks", json={"name": "Unattached"})
    assert res.status_code == 422
    assert not global_create_env["authz"].calls


def test_global_create_rejects_unauthorized_project(global_create_env):
    project_id = global_create_env["project_id"]
    global_create_env["authz"].fail = (
        403,
        "You are not an active member of the project's organization",
    )

    res = client.post(
        f"/api/v1/benchmarks?project_id={project_id}", json={"name": "Sneaky"}
    )
    assert res.status_code == 403
    assert not global_create_env["calls"]


def test_global_create_rejects_unknown_project(global_create_env):
    project_id = global_create_env["project_id"]
    global_create_env["authz"].fail = (404, "Project not found")

    res = client.post(
        f"/api/v1/benchmarks?project_id={project_id}", json={"name": "Ghost"}
    )
    assert res.status_code == 404
    assert not global_create_env["calls"]


def test_global_create_authorized_project_succeeds(global_create_env):
    project_id = global_create_env["project_id"]

    res = client.post(
        f"/api/v1/benchmarks?project_id={project_id}", json={"name": "Attached"}
    )
    assert res.status_code == 201
    body = res.json()
    assert body.get("success", True) is True
    assert body["data"]["project_id"] == str(project_id)

    # Authorization was checked against the explicit project with write roles.
    authz_call = global_create_env["authz"].calls[-1]
    assert authz_call["project_id"] == project_id
    assert authz_call["user_id"] == global_create_env["user_id"]

    create_call = global_create_env["calls"][-1]
    assert create_call["project_id"] == project_id
    assert create_call["author_id"] == global_create_env["user_id"]
