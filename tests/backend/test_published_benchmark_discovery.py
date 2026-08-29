"""Slice 2 — published benchmark discovery & real submission authorization.

Expected behavior (backend-only):
- ``GET /benchmarks/{id}`` and ``GET /benchmarks/{id}/versions`` are readable by
  any authenticated user when the benchmark is **published**; drafts stay
  gated behind active membership of the benchmark's organization.
- ``POST /benchmarks/{version_id}/executions`` is authorized when the benchmark
  is published OR the caller is an active member of its organization.
- ``GET /executions/dispatch-targets`` exposes published benchmarks plus drafts
  owned by the caller's organizations, never drafts of other organizations.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.core import (
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
    Project,
    User,
)
from packages.execution_engine.domain.models import Execution, ExecutionState

DATASET_VERSION_ID = UUID("00000000-0000-0000-0000-000000000006")


def _org(session, name: str) -> Organization:
    org = Organization(name=name, slug=f"{name.lower()}-{uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    return org


def _user(session) -> User:
    user = User(
        full_name="Slice 2 Tester",
        email=f"{uuid4().hex}@test.dev",
        is_active=True,
        is_verified=True,
    )
    session.add(user)
    session.flush()
    return user


def _member(session, user: User, org: Organization, role=OrganizationRole.MEMBER) -> OrganizationMember:
    member = OrganizationMember(
        user_id=user.id,
        organization_id=org.id,
        role=role,
        status=MembershipStatus.ACTIVE,
    )
    session.add(member)
    session.flush()
    return member


def _project(session, org: Organization, name: str) -> Project:
    project = Project(name=name, slug=f"proj-{uuid4().hex[:8]}", org_id=org.id)
    session.add(project)
    session.flush()
    return project


def _benchmark(session, project: Project, *, name: str, status: str) -> Benchmark:
    benchmark = Benchmark(
        project_id=project.id,
        name=name,
        status=status,
        visibility="public" if status == "published" else "private",
    )
    session.add(benchmark)
    session.flush()
    return benchmark


def _version(session, benchmark: Benchmark, version_string: str = "1.0.0") -> BenchmarkVersion:
    version = BenchmarkVersion(
        benchmark_id=benchmark.id,
        version_string=version_string,
        primary_dataset_version_id=DATASET_VERSION_ID,
    )
    session.add(version)
    session.flush()
    return version


@pytest.fixture
def client_context(db_session):
    from apps.backend.dependencies import (
        get_benchmark_app_service,
        get_db_session,
        require_authenticated,
    )
    from apps.backend.services.benchmarks import BenchmarkApplicationService
    from atlas_db.repositories.authoring import (
        BenchmarkCategoryRepository,
        BenchmarkLifecycleRepository,
        BenchmarkRepository,
        BenchmarkVersionRepository,
        CapabilityRepository,
    )
    from atlas_db.services.benchmark_service import BenchmarkService

    benchmark_repo = BenchmarkRepository(db_session)
    app_service = BenchmarkApplicationService(
        domain_service=BenchmarkService(
            benchmark_repo=benchmark_repo,
            lifecycle_repo=BenchmarkLifecycleRepository(db_session),
            version_repo=BenchmarkVersionRepository(db_session),
        ),
        benchmark_repo=benchmark_repo,
        category_repo=BenchmarkCategoryRepository(db_session),
        capability_repo=CapabilityRepository(db_session),
    )
    current_claims = [TokenClaims(sub=uuid4(), exp=0, iat=0, jti=uuid4())]

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_benchmark_app_service] = lambda: app_service
    app.dependency_overrides[require_authenticated] = lambda: current_claims[0]
    yield SimpleNamespace(client=TestClient(app), claims=current_claims)
    app.dependency_overrides.clear()


@pytest.fixture
def exec_service(mock_wake):
    from apps.backend.routers.executions import get_execution_service
    from packages.execution_engine.application.execution_app_service import (
        ExecutionApplicationService,
    )

    service = MagicMock(spec=ExecutionApplicationService)
    app.dependency_overrides[get_execution_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_execution_service, None)


@pytest.fixture
def mock_wake(monkeypatch):
    monkeypatch.setattr("apps.backend.routers.executions.notify_worker_wake", lambda: None)


def _queue_execution_from_service(service: MagicMock, version_id: UUID) -> None:
    execution = Execution(
        id=uuid4(),
        benchmark_version_id=version_id,
        status=ExecutionState.QUEUED,
        max_retries=3,
    )
    service.submit_execution.return_value = execution


# ---------------------------------------------------------------------------
# Published discovery
# ---------------------------------------------------------------------------


def test_get_published_benchmark_readable_by_any_authenticated_user(client_context, db_session):
    org = _org(db_session, "Public Org")
    project = _project(db_session, org, "Public Workspace")
    benchmark = _benchmark(db_session, project, name="HumanEval", status="published")
    db_session.commit()

    # caller is deliberately NOT a member of the benchmark's organization
    response = client_context.client.get(f"/api/v1/benchmarks/{benchmark.id}")

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "HumanEval"


def test_get_draft_benchmark_denied_for_non_member(client_context, db_session):
    org = _org(db_session, "Hidden Org")
    project = _project(db_session, org, "Hidden Workspace")
    benchmark = _benchmark(db_session, project, name="Unreleased", status="draft")
    db_session.commit()

    response = client_context.client.get(f"/api/v1/benchmarks/{benchmark.id}")

    assert response.status_code == 403
    assert "not an active member" in response.text


def test_get_draft_benchmark_allowed_for_active_member(client_context, db_session):
    org = _org(db_session, "Draft Org")
    member_user = _user(db_session)
    _member(db_session, member_user, org)
    project = _project(db_session, org, "Draft Workspace")
    benchmark = _benchmark(db_session, project, name="In Progress", status="draft")
    db_session.commit()

    # act as the organization member
    client_context.claims[0] = TokenClaims(sub=member_user.id, exp=0, iat=0, jti=uuid4())
    db_session.commit()
    response = client_context.client.get(f"/api/v1/benchmarks/{benchmark.id}")

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "In Progress"


def test_get_published_benchmark_versions_readable_by_any_authenticated_user(
    client_context, db_session
):
    org = _org(db_session, "Versions Org")
    project = _project(db_session, org, "Versions Workspace")
    benchmark = _benchmark(db_session, project, name="MBPP", status="published")
    version = _version(db_session, benchmark)
    db_session.commit()

    response = client_context.client.get(f"/api/v1/benchmarks/{benchmark.id}/versions")

    assert response.status_code == 200
    versions = response.json()["data"]
    assert [version.id for version in [version]] == [UUID(item["id"]) for item in versions]


def test_get_draft_benchmark_versions_denied_for_non_member(client_context, db_session):
    org = _org(db_session, "Draft Versions Org")
    project = _project(db_session, org, "Draft Versions Workspace")
    benchmark = _benchmark(db_session, project, name="Unlisted V", status="draft")
    _version(db_session, benchmark)
    db_session.commit()

    response = client_context.client.get(f"/api/v1/benchmarks/{benchmark.id}/versions")

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Submission authorization
# ---------------------------------------------------------------------------


def test_submit_published_benchmark_version_allowed_for_any_authenticated_user(
    client_context, db_session, exec_service, mock_wake
):
    org = _org(db_session, "Submit Org")
    project = _project(db_session, org, "Submit Workspace")
    benchmark = _benchmark(db_session, project, name="GSM8K", status="published")
    version = _version(db_session, benchmark)
    db_session.commit()
    _queue_execution_from_service(exec_service, version.id)

    response = client_context.client.post(
        f"/api/v1/benchmarks/{version.id}/executions", json={"target_model": "mock"}
    )

    assert response.status_code == 201
    assert response.json()["benchmark_version_id"] == str(version.id)
    exec_service.submit_execution.assert_called_once()


def test_submit_draft_benchmark_version_denied_for_non_member(
    client_context, db_session, exec_service, mock_wake
):
    org = _org(db_session, "Restricted Submit Org")
    project = _project(db_session, org, "Restricted Workspace")
    benchmark = _benchmark(db_session, project, name="Unreleased S", status="draft")
    version = _version(db_session, benchmark)
    db_session.commit()

    response = client_context.client.post(
        f"/api/v1/benchmarks/{version.id}/executions",
        json={"benchmark_version_id": str(version.id), "target_model": "mock"},
    )

    assert response.status_code == 403
    assert "not an active member" in response.text
    exec_service.submit_execution.assert_not_called()


def test_submit_draft_benchmark_version_allowed_for_org_member(
    client_context, db_session, exec_service, mock_wake
):
    org = _org(db_session, "Member Submit Org")
    member_user = _user(db_session)
    _member(db_session, member_user, org)
    project = _project(db_session, org, "Member Workspace")
    benchmark = _benchmark(db_session, project, name="Team Draft", status="draft")
    version = _version(db_session, benchmark)
    db_session.commit()
    _queue_execution_from_service(exec_service, version.id)

    client_context.claims[0] = TokenClaims(sub=member_user.id, exp=0, iat=0, jti=uuid4())
    db_session.commit()
    response = client_context.client.post(
        f"/api/v1/benchmarks/{version.id}/executions",
        json={"benchmark_version_id": str(version.id), "target_model": "mock"},
    )

    assert response.status_code == 201
    exec_service.submit_execution.assert_called_once()


def test_submit_missing_benchmark_version_returns_404(client_context, db_session, exec_service, mock_wake):
    unknown = uuid4()
    db_session.commit()

    response = client_context.client.post(
        f"/api/v1/benchmarks/{unknown}/executions",
        json={"benchmark_version_id": str(unknown), "target_model": "mock"},
    )

    assert response.status_code == 404
    exec_service.submit_execution.assert_not_called()


def test_submit_invalid_benchmark_version_id_returns_422(client_context, db_session, exec_service, mock_wake):
    response = client_context.client.post(
        "/api/v1/benchmarks/not-a-uuid/executions", json={"target_model": "mock"}
    )

    assert response.status_code == 422
    exec_service.submit_execution.assert_not_called()


# ---------------------------------------------------------------------------
# Dispatch targets
# ---------------------------------------------------------------------------


def test_dispatch_targets_expose_published_and_own_org_drafts_only(
    client_context, db_session
):
    me = _user(db_session)
    my_org = _org(db_session, "Mine Org")
    _member(db_session, me, my_org)
    their_org = _org(db_session, "Theirs Org")
    public_org = _org(db_session, "Publishing Org")
    db_session.commit()

    my_project = _project(db_session, my_org, "Mine Workspace")
    mine = _benchmark(db_session, my_project, name="My Draft", status="draft")
    mine_version = _version(db_session, mine)

    their_project = _project(db_session, their_org, "Their Workspace")
    theirs = _benchmark(db_session, their_project, name="Their Draft", status="draft")
    _version(db_session, theirs)

    public_project = _project(db_session, public_org, "Public Workspace")
    published = _benchmark(db_session, public_project, name="Public Benchmark", status="published")
    published_version = _version(db_session, published)
    db_session.commit()

    client_context.claims[0] = TokenClaims(sub=me.id, exp=0, iat=0, jti=uuid4())

    response = client_context.client.get("/api/v1/executions/dispatch-targets")

    assert response.status_code == 200
    targets = response.json()
    returned_names = {item["benchmark_name"] for item in targets}
    assert "My Draft" in returned_names
    assert "Public Benchmark" in returned_names
    assert "Their Draft" not in returned_names
    returned_version_ids = {UUID(item["benchmark_version_id"]) for item in targets}
    assert {mine_version.id, published_version.id} <= returned_version_ids
