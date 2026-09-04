import uuid
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import get_search_service, require_authenticated
from apps.backend.main import app
from apps.backend.schemas.search import SearchResult
from services.search.service import SearchService


@pytest.fixture
def mock_search_service():
    service = Mock(spec=SearchService)
    return service


@pytest.fixture
def mock_authz_service():
    service = Mock(spec=ProjectAuthorizationService)
    service.authorize_project_access.return_value = Mock(id=uuid.uuid4())
    return service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_token_claims():
    from apps.backend.schemas.auth import TokenClaims

    return TokenClaims(
        sub=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        exp=9999999999,
        iat=1600000000,
        jti=uuid.uuid4(),
    )


def _result(i: int, entity: str = "benchmark") -> SearchResult:
    return SearchResult(
        id=uuid.UUID(f"00000000-0000-0000-0000-0000000000{i:02d}"),
        entity_type=entity,
        title=f"Result {i}",
        subtitle="Status: PUBLISHED",
        description=None,
        url=f"/{entity}s/{i}",
        score=0.9,
        metadata={"project_id": str(uuid.uuid4()), "status": "PUBLISHED"},
    )


@contextmanager
def _override_project(
    mock_search_service, mock_authz_service, mock_token_claims
):
    app.dependency_overrides[get_search_service] = lambda: mock_search_service
    app.dependency_overrides[get_project_authz_service] = lambda: mock_authz_service
    app.dependency_overrides[require_authenticated] = lambda: mock_token_claims
    yield
    app.dependency_overrides.clear()


class TestProjectScopedSearch:
    def test_returns_scoped_results(self, client, mock_search_service, mock_authz_service, mock_token_claims):
        project_id = uuid.uuid4()
        mock_search_service.search_all.return_value = [_result(1), _result(2, "execution")]

        with _override_project(mock_search_service, mock_authz_service, mock_token_claims):
            resp = client.get(
                f"/api/v1/projects/{project_id}/search", params={"q": "counting", "limit": 5}
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["items"][0]["entity_type"] == "benchmark"
        # The service must be invoked scoped to EXACTLY this project.
        mock_search_service.search_all.assert_called_once()
        args = mock_search_service.search_all.call_args
        assert args.kwargs["project_ids"] == [project_id]

    def test_authz_enforced(self, client, mock_search_service, mock_authz_service, mock_token_claims):
        project_id = uuid.uuid4()
        mock_authz_service.authorize_project_access.side_effect = HTTPException(
            status_code=404, detail="Project not found"
        )

        with _override_project(mock_search_service, mock_authz_service, mock_token_claims):
            resp = client.get(
                f"/api/v1/projects/{project_id}/search", params={"q": "x"}
            )

        assert resp.status_code == 404
        mock_authz_service.authorize_project_access.assert_called_once()
        call_kwargs = mock_authz_service.authorize_project_access.call_args.kwargs
        assert call_kwargs["project_id"] == project_id
        assert call_kwargs["user_id"] == mock_token_claims.sub
        mock_search_service.search_all.assert_not_called()

    def test_requires_authentication(self, client):
        project_id = uuid.uuid4()
        # No override of require_authenticated -> real auth middleware -> 401.
        resp = client.get(f"/api/v1/projects/{project_id}/search", params={"q": "x"})
        assert resp.status_code == 401


class TestGlobalSearchHardened:
    def test_requires_authentication(self, client):
        # The hardening is proven: without a token, the global endpoint is rejected.
        resp = client.get("/api/v1/search", params={"q": "x"})
        assert resp.status_code == 401

    def test_scopes_to_accessible_projects(
        self, client, mock_search_service, mock_token_claims, monkeypatch
    ):
        from apps.backend.routers import search as search_router

        accessible = [uuid.uuid4(), uuid.uuid4()]
        monkeypatch.setattr(
            search_router, "resolve_accessible_project_ids", lambda db, user_id: accessible
        )
        mock_search_service.search_all.return_value = [_result(3)]

        app.dependency_overrides[get_search_service] = lambda: mock_search_service
        app.dependency_overrides[require_authenticated] = lambda: mock_token_claims

        try:
            resp = client.get("/api/v1/search", params={"q": "x"})
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        mock_search_service.search_all.assert_called_once()
        assert mock_search_service.search_all.call_args.kwargs["project_ids"] == accessible

    def test_scopes_to_empty_when_no_memberships(
        self, client, mock_search_service, mock_token_claims, monkeypatch
    ):
        from apps.backend.routers import search as search_router

        monkeypatch.setattr(
            search_router, "resolve_accessible_project_ids", lambda db, user_id: []
        )
        mock_search_service.search_all.return_value = []

        app.dependency_overrides[get_search_service] = lambda: mock_search_service
        app.dependency_overrides[require_authenticated] = lambda: mock_token_claims
        try:
            resp = client.get("/api/v1/search", params={"q": "x"})
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert mock_search_service.search_all.call_args.kwargs["project_ids"] == []
