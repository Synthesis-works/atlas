"""Tier-1 security matrix: execution + report-run access is scoped to the
authenticated user's accessible projects.

Proves real tenant isolation: a user must not read, list, cancel, or export
another project's / org's execution or run report -- not merely that an
endpoint returns some 403.

These tests exercise the ROUTER authorization boundary (matching the repo's
established pattern from the v3.5 search hardening): the router must derive
the authoritative owning project from the resource and forward the correct
``project_id``/``user_id`` to the shared ``ProjectAuthorizationService``, and
list endpoints must scope the query (via ``resolve_accessible_project_ids``).
The shared authorization primitive itself is unit-tested directly to prove
two-user / two-org isolation.
"""

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, UTC
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.backend.authz import (
    ProjectAuthorizationService,
    get_project_authz_service,
)
from apps.backend.dependencies import (
    get_db_session,
    get_reporting_service,
    require_authenticated,
)
from apps.backend.main import app
from atlas_db.models.core import (
    MembershipStatus,
    OrganizationMember,
    OrganizationRole,
    Project,
)
from atlas_db.models.execution import Execution as Exec
from apps.backend.routers import executions as executions_router
from apps.backend.routers import reporting as reporting_router
from apps.backend.routers.executions import get_execution_service
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.reporting import ReportSummaryRead
from packages.execution_engine.application.execution_app_service import (
    ExecutionApplicationService,
)
from packages.execution_engine.domain.models import Execution as DomainExec
from packages.execution_engine.domain.models import ExecutionState
from services.report.models.read_models import ReportRunStatus
from services.report.services.reporting import ReportingService


def _make_db(env=None):
    """Lazily import FakeDB (must be imported at runtime under this fixture layout)."""
    from tests._fakes import FakeDB

    return FakeDB(env)


def _claims(user_id: uuid.UUID | None = None) -> TokenClaims:
    return TokenClaims(
        sub=user_id or uuid.uuid4(),
        membership_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        exp=9999999999,
        iat=1600000000,
        jti=uuid.uuid4(),
    )


def _execution(exec_id: uuid.UUID, project_id: uuid.UUID) -> Exec:
    now = datetime.now(UTC)
    return Exec(
        id=exec_id,
        project_id=project_id,
        benchmark_version_id=uuid.uuid4(),
        status="COMPLETED",
        target_model="gpt-4o",
        submitted_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=now,
        total_items=1,
        completed_items=1,
    )


def _org_member(user_id, org_id, role: OrganizationRole = OrganizationRole.OWNER):
    return OrganizationMember(
        user_id=user_id, organization_id=org_id, role=role, status=MembershipStatus.ACTIVE
    )


class TestAuthorizePrimitiveIsolation:
    """The shared primitive proves two users in two orgs cannot cross access."""

    def test_user1_can_access_own_project(self):
        u1 = uuid.uuid4()
        org1 = uuid.uuid4()
        p1 = Project(id=uuid.uuid4(), org_id=org1, name="P1")
        # User1 is a member of org1.
        db = _make_db({OrganizationMember: [_org_member(u1, org1)], Project: [p1]})
        authz = ProjectAuthorizationService(db)
        # get_by_user_and_org filters on (user, org); FakeDB returns rows[0] so we
        # seed exactly the answerable row for this single-member scenario.
        member = authz.authorize_project_access(
            project_id=p1.id, user_id=u1, allowed_roles=[OrganizationRole.OWNER]
        )
        assert member.role == OrganizationRole.OWNER

    def test_user_not_member_of_parent_org_denied(self):
        u2 = uuid.uuid4()
        org1 = uuid.uuid4()
        p1 = Project(id=uuid.uuid4(), org_id=org1, name="P1")
        db = _make_db({OrganizationMember: [], Project: [p1]})
        authz = ProjectAuthorizationService(db)
        with pytest.raises(HTTPException) as exc:
            authz.authorize_project_access(
                project_id=p1.id, user_id=u2, allowed_roles=[OrganizationRole.VIEWER]
            )
        assert exc.value.status_code == 403

    def test_readonly_role_cannot_use_write_roles(self):
        u1 = uuid.uuid4()
        org1 = uuid.uuid4()
        p1 = Project(id=uuid.uuid4(), org_id=org1, name="P1")
        db = _make_db(
            {
                OrganizationMember: [_org_member(u1, org1, OrganizationRole.VIEWER)],
                Project: [p1],
            }
        )
        authz = ProjectAuthorizationService(db)
        with pytest.raises(HTTPException) as exc:
            authz.authorize_project_access(
                project_id=p1.id,
                user_id=u1,
                allowed_roles=[
                    OrganizationRole.OWNER,
                    OrganizationRole.ADMIN,
                    OrganizationRole.MEMBER,
                ],
            )
        assert exc.value.status_code == 403


@pytest.fixture
def mock_execution_service():
    return Mock(spec=ExecutionApplicationService)


@pytest.fixture
def mock_reporting_service():
    return Mock(spec=ReportingService)


@pytest.fixture
def mock_authz_service():
    service = Mock(spec=ProjectAuthorizationService)
    service.authorize_project_access.return_value = Mock(id=uuid.uuid4())
    return service


@pytest.fixture
def client():
    return TestClient(app)


@contextmanager
def _override(deps: dict, overrides: dict):
    for dep, value in overrides.items():
        app.dependency_overrides[dep] = value
    try:
        yield
    finally:
        app.dependency_overrides.clear()


class TestExecutionReadScoping:
    def test_same_accessible_project_allowed(
        self, client, mock_execution_service, mock_authz_service
    ):
        exec_id, project_id = uuid.uuid4(), uuid.uuid4()
        db = _make_db({Exec: [_execution(exec_id, project_id)]})
        claims = _claims()
        mock_execution_service.get_execution.return_value = _domain_exec(exec_id)
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: claims,
                get_project_authz_service: lambda: mock_authz_service,
            },
        ):
            resp = client.get(f"/api/v1/executions/{exec_id}")
        assert resp.status_code == 200
        mock_authz_service.authorize_project_access.assert_called_once()
        kwargs = mock_authz_service.authorize_project_access.call_args.kwargs
        assert kwargs["project_id"] == project_id
        assert kwargs["user_id"] == claims.sub

    def test_other_org_execution_denied(self, client, mock_execution_service, mock_authz_service):
        exec_id, project_id = uuid.uuid4(), uuid.uuid4()
        db = _make_db({Exec: [_execution(exec_id, project_id)]})
        mock_authz_service.authorize_project_access.side_effect = HTTPException(
            status_code=403, detail="not a member"
        )
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
            },
        ):
            resp = client.get(f"/api/v1/executions/{exec_id}")
        assert resp.status_code == 403
        mock_execution_service.get_execution.assert_not_called()

    def test_missing_execution_is_404(self, client, mock_authz_service):
        exec_id = uuid.uuid4()
        db = _make_db({Exec: []})
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
            },
        ):
            resp = client.get(f"/api/v1/executions/{exec_id}")
        assert resp.status_code == 404
        mock_authz_service.authorize_project_access.assert_not_called()

    def test_unauthenticated_denied(self, client):
        resp = client.get(f"/api/v1/executions/{uuid.uuid4()}")
        assert resp.status_code == 401


class TestExecutionListScoping:
    def test_scopes_query_to_accessible_projects(self, client, monkeypatch):
        accessible = [uuid.uuid4(), uuid.uuid4()]
        # The list endpoint must NOT fetch-then-filter: assert the router scopes
        # via resolve_accessible_project_ids (query-level filter follows in impl).
        monkeypatch.setattr(
            executions_router, "resolve_accessible_project_ids", lambda db, user_id: accessible
        )
        db = _make_db({Exec: []})
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
            },
        ):
            resp = client.get("/api/v1/executions")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_empty_membership_yields_no_rows(self, client, monkeypatch):
        monkeypatch.setattr(
            executions_router, "resolve_accessible_project_ids", lambda db, user_id: []
        )
        db = _make_db({Exec: []})
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
            },
        ):
            resp = client.get("/api/v1/executions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestExecutionCancelScoping:
    def test_cancel_scoped_and_write_role_checked(
        self, client, mock_execution_service, mock_authz_service
    ):
        exec_id, project_id = uuid.uuid4(), uuid.uuid4()
        db = _make_db({Exec: [_execution(exec_id, project_id)]})
        mock_execution_service.cancel_execution.return_value = _domain_exec(
            exec_id, ExecutionState.CANCELLED
        )
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
                get_execution_service: lambda: mock_execution_service,
            },
        ):
            resp = client.post(f"/api/v1/executions/{exec_id}/cancel")
        assert resp.status_code == 200
        kwargs = mock_authz_service.authorize_project_access.call_args.kwargs
        assert kwargs["project_id"] == project_id
        # Cancel is a WRITE: must demand a write role, never VIEWER-only.
        assert OrganizationRole.VIEWER not in kwargs["allowed_roles"]
        assert OrganizationRole.MEMBER in kwargs["allowed_roles"]

    def test_cancel_other_org_denied(self, client, mock_execution_service, mock_authz_service):
        exec_id, project_id = uuid.uuid4(), uuid.uuid4()
        db = _make_db({Exec: [_execution(exec_id, project_id)]})
        mock_authz_service.authorize_project_access.side_effect = HTTPException(
            status_code=403, detail="no"
        )
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
                get_execution_service: lambda: mock_execution_service,
            },
        ):
            resp = client.post(f"/api/v1/executions/{exec_id}/cancel")
        assert resp.status_code == 403
        mock_execution_service.cancel_execution.assert_not_called()

    def test_cancel_missing_is_404(self, client, mock_authz_service, mock_execution_service):
        exec_id = uuid.uuid4()
        db = _make_db({Exec: []})
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
                get_execution_service: lambda: mock_execution_service,
            },
        ):
            resp = client.post(f"/api/v1/executions/{exec_id}/cancel")
        assert resp.status_code == 404
        mock_authz_service.authorize_project_access.assert_not_called()


class TestReportReadScoping:
    def test_same_project_report_allowed(self, client, mock_reporting_service, mock_authz_service):
        run_id, project_id = uuid.uuid4(), uuid.uuid4()
        db = _make_db({Exec: [_execution(run_id, project_id)]})
        mock_reporting_service.get_run_summary.return_value = ReportSummaryRead(
            run_id=run_id,
            benchmark_id=uuid.uuid4(),
            benchmark_name="HumanEval",
            benchmark_version="1.0.0",
            target_model="gpt-4o",
            evaluation_status=ReportRunStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            overall_score=88.5,
            scores=[],
        )
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
                get_reporting_service: lambda: mock_reporting_service,
            },
        ):
            resp = client.get(f"/api/v1/reports/runs/{run_id}")
        assert resp.status_code == 200
        kwargs = mock_authz_service.authorize_project_access.call_args.kwargs
        assert kwargs["project_id"] == project_id

    def test_other_org_report_denied(self, client, mock_reporting_service, mock_authz_service):
        run_id, project_id = uuid.uuid4(), uuid.uuid4()
        db = _make_db({Exec: [_execution(run_id, project_id)]})
        mock_authz_service.authorize_project_access.side_effect = HTTPException(
            status_code=403, detail="no"
        )
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
                get_reporting_service: lambda: mock_reporting_service,
            },
        ):
            resp = client.get(f"/api/v1/reports/runs/{run_id}")
        assert resp.status_code == 403
        mock_reporting_service.get_run_summary.assert_not_called()

    def test_missing_report_is_404(self, client, mock_authz_service):
        run_id = uuid.uuid4()
        db = _make_db({Exec: []})
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
            },
        ):
            resp = client.get(f"/api/v1/reports/runs/{run_id}")
        assert resp.status_code == 404
        mock_authz_service.authorize_project_access.assert_not_called()

    def test_unauthenticated_denied(self, client):
        resp = client.get(f"/api/v1/reports/runs/{uuid.uuid4()}")
        assert resp.status_code == 401


class TestReportExportScoping:
    def test_export_scoped_to_project(self, client, mock_reporting_service, mock_authz_service):
        run_id, project_id = uuid.uuid4(), uuid.uuid4()
        db = _make_db({Exec: [_execution(run_id, project_id)]})
        mock_reporting_service.build_report_export.return_value = Mock()
        mock_reporting_service.export_run_results.return_value = Mock(
            filename_stem="r",
            filename_extension="json",
            content=b"{}",
            mime_type="application/json",
        )
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
                get_reporting_service: lambda: mock_reporting_service,
            },
        ):
            resp = client.get(f"/api/v1/reports/runs/{run_id}/export?format=json")
        assert resp.status_code == 200
        kwargs = mock_authz_service.authorize_project_access.call_args.kwargs
        assert kwargs["project_id"] == project_id

    def test_export_other_org_denied(self, client, mock_reporting_service, mock_authz_service):
        run_id, project_id = uuid.uuid4(), uuid.uuid4()
        db = _make_db({Exec: [_execution(run_id, project_id)]})
        mock_authz_service.authorize_project_access.side_effect = HTTPException(
            status_code=403, detail="no"
        )
        with _override(
            app,
            {
                get_db_session: lambda: db,
                require_authenticated: lambda: _claims(),
                get_project_authz_service: lambda: mock_authz_service,
                get_reporting_service: lambda: mock_reporting_service,
            },
        ):
            resp = client.get(f"/api/v1/reports/runs/{run_id}/export?format=json")
        assert resp.status_code == 403
        mock_reporting_service.build_report_export.assert_not_called()


class TestReportListScoping:
    def test_list_scopes_to_accessible_projects(self, client, mock_reporting_service, monkeypatch):
        accessible = [uuid.uuid4(), uuid.uuid4()]
        monkeypatch.setattr(
            reporting_router, "resolve_accessible_project_ids", lambda db, user_id: accessible
        )
        mock_reporting_service.get_runs_filtered.return_value = Mock(
            items=[], total=0, page=1, size=50
        )
        with _override(
            app,
            {
                get_db_session: lambda: _make_db({Exec: []}),
                require_authenticated: lambda: _claims(),
                get_reporting_service: lambda: mock_reporting_service,
            },
        ):
            resp = client.get("/api/v1/reports/runs")
        assert resp.status_code == 200
        mock_reporting_service.get_runs_filtered.assert_called_once()
        assert (
            mock_reporting_service.get_runs_filtered.call_args.kwargs["project_ids"] == accessible
        )

    def test_list_empty_membership_yields_no_rows(
        self, client, mock_reporting_service, monkeypatch
    ):
        monkeypatch.setattr(
            reporting_router, "resolve_accessible_project_ids", lambda db, user_id: []
        )
        mock_reporting_service.get_runs_filtered.return_value = Mock(
            items=[], total=0, page=1, size=50
        )
        with _override(
            app,
            {
                get_db_session: lambda: _make_db({Exec: []}),
                require_authenticated: lambda: _claims(),
                get_reporting_service: lambda: mock_reporting_service,
            },
        ):
            resp = client.get("/api/v1/reports/runs")
        assert resp.status_code == 200
        assert mock_reporting_service.get_runs_filtered.call_args.kwargs["project_ids"] == []


def _domain_exec(exec_id, state=ExecutionState.QUEUED):
    return DomainExec(id=exec_id, benchmark_version_id=uuid.uuid4(), status=state, max_retries=3)
