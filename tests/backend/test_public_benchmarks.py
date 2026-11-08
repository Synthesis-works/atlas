"""The anonymous benchmark catalogue served to the organisation site.

The marketing page at synthesis-works.xyz has no session, so
``GET /api/v1/public/benchmarks`` must work with no Authorization header while
never exposing drafts or tenant identifiers.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.backend.config import Settings, settings
from apps.backend.main import app, create_app
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.core import Organization, Project


def _org(session) -> Organization:
    org = Organization(name="Public Org", slug=f"public-{uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    return org


def _project(session, org: Organization) -> Project:
    project = Project(name="Public Project", slug=f"proj-{uuid4().hex[:8]}", org_id=org.id)
    session.add(project)
    session.flush()
    return project


def _benchmark(session, project: Project, *, name: str, status: str) -> Benchmark:
    benchmark = Benchmark(project_id=project.id, name=name, status=status)
    session.add(benchmark)
    session.flush()
    return benchmark


def _version(session, benchmark: Benchmark, version_string: str = "1.0.0") -> BenchmarkVersion:
    version = BenchmarkVersion(benchmark_id=benchmark.id, version_string=version_string)
    session.add(version)
    session.flush()
    return version


@pytest.fixture
def anonymous_client(db_session):
    from apps.backend.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_public_catalogue_lists_published_benchmarks_without_a_token(anonymous_client, db_session):
    project = _project(db_session, _org(db_session))
    published = _benchmark(db_session, project, name="HumanEval", status="published")
    _version(db_session, published, version_string="2.1.0")
    _benchmark(db_session, project, name="Internal Draft", status="draft")

    response = anonymous_client.get("/api/v1/public/benchmarks")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    items = body["data"]["items"]
    assert [item["name"] for item in items] == ["HumanEval"]

    item = items[0]
    assert item["state"] == "published"
    assert item["versions"][0]["version_string"] == "2.1.0"
    # The catalogue is public; the owning project is not.
    assert "project_id" not in item


def test_public_catalogue_is_cacheable(anonymous_client, db_session):
    project = _project(db_session, _org(db_session))
    _benchmark(db_session, project, name="MBPP", status="published")

    response = anonymous_client.get("/api/v1/public/benchmarks")

    assert response.status_code == 200
    assert "max-age=60" in response.headers["cache-control"]


def test_public_catalogue_hides_every_draft(anonymous_client, db_session):
    project = _project(db_session, _org(db_session))
    _benchmark(db_session, project, name="Proposal", status="proposal")
    _benchmark(db_session, project, name="Draft", status="draft")
    _benchmark(db_session, project, name="In Review", status="review")

    response = anonymous_client.get("/api/v1/public/benchmarks")

    assert response.status_code == 200
    assert response.json()["data"]["items"] == []
    assert response.json()["data"]["total"] == 0


def test_default_cors_origins_include_the_organisation_site():
    defaults = Settings.model_fields["cors_origins"].default_factory()

    assert "https://synthesis-works.xyz" in defaults
    assert "https://synthesis-works-web.vercel.app" in defaults


def test_cors_preflight_allows_the_organisation_site(monkeypatch):
    origins = list(settings.cors_origins)
    if "https://synthesis-works.xyz" not in origins:
        origins.append("https://synthesis-works.xyz")
    monkeypatch.setattr(settings, "cors_origins", origins)

    client = TestClient(create_app())
    response = client.options(
        "/api/v1/public/benchmarks",
        headers={
            "Origin": "https://synthesis-works.xyz",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://synthesis-works.xyz"
