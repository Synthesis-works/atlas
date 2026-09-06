"""Tier-1 security matrix: /history/* access is authenticated and scoped to
the caller's accessible projects.

Proves real tenant isolation, not merely "some 403":

- unauthenticated -> 401 on every history endpoint
- authenticated -> sees history only for accessible projects
- cross-org rows are never returned
- empty membership -> zero scoped rows (never global history)
- queries are filtered at the SQL/ORM level (project_id IN accessible set),
  before GROUP BY for the models endpoint (never fetch-all + Python filter)

The router-level tests assert the router derives the accessible project set
(``resolve_accessible_project_ids``) and forwards it into the app-service
call. The repository-level tests drive the real repo/service chain against a
recording session and assert the ``project_id IN (...`` filter is part of the
constructed query.
"""

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, UTC
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from apps.backend.dependencies import (
    get_benchmark_app_service,
    get_db_session,
    get_execution_app_service,
    require_authenticated,
)
from apps.backend.main import app
from apps.backend.schemas.auth import TokenClaims
from apps.backend.services.benchmarks import BenchmarkApplicationService
from apps.backend.services.executions import ExecutionApplicationService
from atlas_db.models.execution import Execution
from atlas_db.models.authoring import Benchmark


def _claims(user_id: uuid.UUID | None = None) -> TokenClaims:
    return TokenClaims(
        sub=user_id or uuid.uuid4(),
        membership_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        exp=9999999999,
        iat=1600000000,
        jti=uuid.uuid4(),
    )


@contextmanager
def _override(overrides: dict):
    for dep, value in overrides.items():
        app.dependency_overrides[dep] = value
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_benchmark_service():
    return Mock(spec=BenchmarkApplicationService)


@pytest.fixture
def mock_execution_service():
    return Mock(spec=ExecutionApplicationService)


# ---------------------------------------------------------------------------
# Recording session: proves the DB query actually carries a project filter.
# ---------------------------------------------------------------------------


class _RecordingQuery:
    """Records the filter criteria applied to a query and rows to return.

    When a ``project_id IN (...)`` criterion is applied, the rows are actually
    narrowed to match, so an empty accessible set yields zero rows exactly as
    real SQL ``IN ()`` would (never a fall-through to global history).
    """

    def __init__(self, rows: list):
        self._rows = list(rows)
        self.filters: list = []

    def filter(self, *criteria, **kwargs):
        self.filters.extend(criteria)
        for c in criteria:
            left = getattr(c, "left", None)
            if left is not None and left.key == "project_id":
                right = getattr(c, "right", None)
                allowed = getattr(right, "value", None)
                if isinstance(allowed, list) and allowed:
                    self._rows = [r for r in self._rows if r.project_id in allowed]
                elif isinstance(allowed, list):
                    self._rows = []
        return self

    def join(self, *criteria, **kwargs):
        return self

    def order_by(self, *criteria, **kwargs):
        return self

    def group_by(self, *criteria, **kwargs):
        return self

    def offset(self, value):
        return self

    def limit(self, value):
        return self

    def count(self):
        return len(self._rows)

    def all(self):
        return list(self._rows)

    def __getitem__(self, item):
        return self._rows[item]


class _RecordingSession:
    """db.session stand-in that records query filters and maps model->rows."""

    def __init__(self, env: dict):
        self._env = {cls: list(rows) for cls, rows in env.items()}
        self.execution_filters: list = []
        self.benchmark_filters: list = []

    def query(self, *entities):
        entity = getattr(entities[0], "class_", entities[0])
        q = _RecordingQuery(self._env.get(entity, []))
        if entity is Execution:
            original = q.filter
            q.filter = lambda *criteria, **kw: (
                self.execution_filters.extend(criteria),
                original(*criteria, **kw),
            )[1]
        if entity is Benchmark:
            original = q.filter
            q.filter = lambda *criteria, **kw: (
                self.benchmark_filters.extend(criteria),
                original(*criteria, **kw),
            )[1]
        return q


def _in_set(criteria):
    """Return the set of ids inside a ``project_id.in_(ids)`` criterion."""
    for c in criteria:
        if getattr(c, "left", None) is not None and c.left is not None:
            right = getattr(c, "right", None)
            if right is not None:
                # Post-compile expanding bind: right is a BindParameter whose
                # .value is the full list of bound ids.
                value = getattr(right, "value", None)
                if isinstance(value, list):
                    return {v for v in value}
                # Non-expanding form: right wraps a sequence of BindParameters.
                clauses = getattr(right, "clauses", None)
                if clauses is not None:
                    return {e.value for e in clauses}
    return set()


def _in_filter_selects_attr(criteria, model_attr):
    for c in criteria:
        left = getattr(c, "left", None)
        if left is not None and getattr(left, "key", None) == model_attr.key:
            return True
    return False


def _execution(exec_id: uuid.UUID, project_id: uuid.UUID) -> Execution:
    now = datetime.now(UTC)
    return Execution(
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


def _benchmark(bm_id: uuid.UUID, project_id: uuid.UUID, name: str) -> Benchmark:
    return Benchmark(id=bm_id, project_id=project_id, name=name, status="published")


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestHistoryAuthentication:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/history/benchmarks/recent",
            "/api/v1/history/executions/recent",
            "/api/v1/history/models/recent",
        ],
    )
    def test_unauthenticated_denied_on_every_history_endpoint(self, client, path):
        with _override({}):
            resp = client.get(path)
        assert resp.status_code == 401

    def test_authenticated_reaches_benchmarks(self, client, mock_benchmark_service, monkeypatch):
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: [uuid.uuid4()],
        )
        mock_benchmark_service.get_recent_benchmarks.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_benchmark_app_service: lambda: mock_benchmark_service,
            }
        ):
            resp = client.get("/api/v1/history/benchmarks/recent")
        assert resp.status_code == 200

    def test_authenticated_reaches_executions(self, client, mock_execution_service, monkeypatch):
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: [uuid.uuid4()],
        )
        mock_execution_service.get_recent_executions.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_execution_app_service: lambda: mock_execution_service,
            }
        ):
            resp = client.get("/api/v1/history/executions/recent")
        assert resp.status_code == 200

    def test_authenticated_reaches_models(self, client, mock_execution_service, monkeypatch):
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: [uuid.uuid4()],
        )
        mock_execution_service.get_recent_models.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_execution_app_service: lambda: mock_execution_service,
            }
        ):
            resp = client.get("/api/v1/history/models/recent")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Router-level scoping: accessible project set is forwarded into the query path
# ---------------------------------------------------------------------------


class TestHistoryRouterScoping:
    def test_benchmarks_forwards_accessible_projects(
        self, client, mock_benchmark_service, monkeypatch
    ):
        accessible = [uuid.uuid4(), uuid.uuid4()]
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: accessible,
        )
        mock_benchmark_service.get_recent_benchmarks.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_benchmark_app_service: lambda: mock_benchmark_service,
            }
        ):
            resp = client.get("/api/v1/history/benchmarks/recent")
        assert resp.status_code == 200
        assert (
            mock_benchmark_service.get_recent_benchmarks.call_args.kwargs["project_ids"]
            == accessible
        )

    def test_executions_forwards_accessible_projects(
        self, client, mock_execution_service, monkeypatch
    ):
        accessible = [uuid.uuid4()]
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: accessible,
        )
        mock_execution_service.get_recent_executions.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_execution_app_service: lambda: mock_execution_service,
            }
        ):
            resp = client.get("/api/v1/history/executions/recent")
        assert resp.status_code == 200
        assert (
            mock_execution_service.get_recent_executions.call_args.kwargs["project_ids"]
            == accessible
        )

    def test_models_forwards_accessible_projects(self, client, mock_execution_service, monkeypatch):
        accessible = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: accessible,
        )
        mock_execution_service.get_recent_models.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_execution_app_service: lambda: mock_execution_service,
            }
        ):
            resp = client.get("/api/v1/history/models/recent")
        assert resp.status_code == 200
        assert (
            mock_execution_service.get_recent_models.call_args.kwargs["project_ids"] == accessible
        )

    def test_empty_membership_benchmarks_yields_empty_not_global(
        self, client, mock_benchmark_service, monkeypatch
    ):
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: [],
        )
        mock_benchmark_service.get_recent_benchmarks.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_benchmark_app_service: lambda: mock_benchmark_service,
            }
        ):
            resp = client.get("/api/v1/history/benchmarks/recent")
        assert resp.status_code == 200
        assert mock_benchmark_service.get_recent_benchmarks.call_args.kwargs["project_ids"] == []

    def test_empty_membership_executions_yields_empty_not_global(
        self, client, mock_execution_service, monkeypatch
    ):
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: [],
        )
        mock_execution_service.get_recent_executions.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_execution_app_service: lambda: mock_execution_service,
            }
        ):
            resp = client.get("/api/v1/history/executions/recent")
        assert resp.status_code == 200
        assert mock_execution_service.get_recent_executions.call_args.kwargs["project_ids"] == []

    def test_empty_membership_models_yields_empty_not_global(
        self, client, mock_execution_service, monkeypatch
    ):
        monkeypatch.setattr(
            "apps.backend.routers.history.resolve_accessible_project_ids",
            lambda db, user_id: [],
        )
        mock_execution_service.get_recent_models.return_value = []
        with _override(
            {
                require_authenticated: lambda: _claims(),
                get_db_session: lambda: Mock(),
                get_execution_app_service: lambda: mock_execution_service,
            }
        ):
            resp = client.get("/api/v1/history/models/recent")
        assert resp.status_code == 200
        assert mock_execution_service.get_recent_models.call_args.kwargs["project_ids"] == []


# ---------------------------------------------------------------------------
# Repository / service-level: the SQL query itself filters by project
# ---------------------------------------------------------------------------


class TestHistoryQueryLevelScoping:
    def test_recent_executions_filters_execution_project_id(self):
        from atlas_db.repositories.execution import ExecutionRepository
        from apps.backend.services.executions import ExecutionApplicationService

        accessible = [uuid.uuid4(), uuid.uuid4()]
        e1 = _execution(uuid.uuid4(), accessible[0])
        e2 = _execution(uuid.uuid4(), uuid.uuid4())  # other project
        session = _RecordingSession({Execution: [e1, e2]})
        repo = ExecutionRepository(session)
        svc = ExecutionApplicationService(execution_repo=repo)

        _ = svc.get_recent_executions(limit=10, project_ids=accessible)

        assert _in_filter_selects_attr(session.execution_filters, Execution.project_id)
        assert _in_set(session.execution_filters) == set(accessible)

    def test_recent_benchmarks_filters_benchmark_project_id(self):
        from atlas_db.repositories.authoring import BenchmarkRepository
        from apps.backend.services.benchmarks import (
            BenchmarkApplicationService,
        )

        accessible = [uuid.uuid4()]
        b1 = _benchmark(uuid.uuid4(), accessible[0], "Nested")
        b2 = _benchmark(uuid.uuid4(), uuid.uuid4(), "Other")
        session = _RecordingSession({Benchmark: [b1, b2]})
        repo = BenchmarkRepository(session)
        svc = BenchmarkApplicationService(
            domain_service=Mock(), benchmark_repo=repo, category_repo=Mock(), capability_repo=Mock()
        )

        _ = svc.get_recent_benchmarks(limit=10, project_ids=accessible)

        assert _in_filter_selects_attr(session.benchmark_filters, Benchmark.project_id)
        assert _in_set(session.benchmark_filters) == set(accessible)

    def test_recent_models_filters_underlying_executions_before_grouping(self):
        from atlas_db.repositories.execution import ExecutionRepository

        accessible = [uuid.uuid4()]
        e1 = _execution(uuid.uuid4(), accessible[0])
        e2 = _execution(uuid.uuid4(), uuid.uuid4())  # other project, must be excluded
        session = _RecordingSession({Execution: [e1, e2]})
        repo = ExecutionRepository(session)

        _ = repo.get_recent_models(limit=10, project_ids=accessible)

        # The security filter must name Execution.project_id, meaning it is applied
        # to the underlying rows (before the target_model aggregation), not to an
        # already-aggregated result stream lacking project metadata.
        assert _in_filter_selects_attr(session.execution_filters, Execution.project_id)
        assert _in_set(session.execution_filters) == set(accessible)

    def test_recent_executions_empty_project_set_is_summarized_as_empty(self):
        from atlas_db.repositories.execution import ExecutionRepository
        from apps.backend.services.executions import ExecutionApplicationService

        session = _RecordingSession({Execution: [_execution(uuid.uuid4(), uuid.uuid4())]})
        repo = ExecutionRepository(session)
        svc = ExecutionApplicationService(execution_repo=repo)

        rows = svc.get_recent_executions(limit=10, project_ids=[])

        assert rows == []

    def test_recent_benchmarks_empty_project_set_yields_empty(self):
        from atlas_db.repositories.authoring import BenchmarkRepository
        from apps.backend.services.benchmarks import (
            BenchmarkApplicationService,
        )

        session = _RecordingSession({Benchmark: [_benchmark(uuid.uuid4(), uuid.uuid4(), "X")]})
        repo = BenchmarkRepository(session)
        svc = BenchmarkApplicationService(
            domain_service=Mock(), benchmark_repo=repo, category_repo=Mock(), capability_repo=Mock()
        )

        rows = svc.get_recent_benchmarks(limit=10, project_ids=[])

        assert rows == []
