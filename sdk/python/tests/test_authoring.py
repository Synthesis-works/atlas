"""Tests for the AtlasClient benchmark-authoring + discovery methods (v3.2).

Uses ``pytest-httpx`` for a mock transport; no live Atlas deployment required.
"""

from __future__ import annotations

import pytest

from atlas_sdk.auth import StaticTokenSupplier
from atlas_sdk.client import AtlasClient


def _ok(data: dict | list | None, *, message: str = "ok") -> dict:
    """Wrap *data* in the standard ``APIResponse`` envelope."""
    return {
        "success": True,
        "message": message,
        "data": data,
        "meta": {"request_id": "req-1", "timestamp": "2026-01-01T00:00:00Z"},
    }


PROJECT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
BENCH_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
VERSION_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
ORG_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"


def _client() -> AtlasClient:
    return AtlasClient("http://localhost:8000", token_supplier=StaticTokenSupplier("t"))


class TestCreateBenchmark:
    def test_create_benchmark(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/benchmarks",
            json=_ok(
                {
                    "id": BENCH_ID,
                    "project_id": PROJECT_ID,
                    "state": "draft",
                    "name": "My Bench",
                }
            ),
            status_code=201,
        )
        client = _client()
        bench = client.create_benchmark(PROJECT_ID, name="My Bench")
        assert str(bench.id) == BENCH_ID
        assert bench.state == "draft"
        client.close()

    def test_create_benchmark_sends_body(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/benchmarks",
            json=_ok({"id": BENCH_ID, "project_id": PROJECT_ID, "state": "draft", "name": "X"}),
            status_code=201,
        )
        client = _client()
        client.create_benchmark(
            PROJECT_ID,
            name="X",
            objective="obj",
            category_ids=["11111111-0000-0000-0000-000000000000"],
            capability_ids=["22222222-0000-0000-0000-000000000000"],
        )
        request = httpx_mock.get_request()
        assert request is not None
        payload = request.read().decode()
        assert '"name":"X"' in payload
        assert '"objective":"obj"' in payload
        assert "11111111-0000-0000-0000-000000000000" in payload
        client.close()


class TestUpdateBenchmark:
    def test_update_benchmark(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="PUT",
            url=f"http://localhost:8000/api/v1/benchmarks/{BENCH_ID}",
            json=_ok({"id": BENCH_ID, "project_id": PROJECT_ID, "state": "draft", "name": "New"}),
        )
        client = _client()
        bench = client.update_benchmark(BENCH_ID, name="New")
        assert bench.name == "New"
        client.close()

    def test_update_only_provided_fields(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="PUT",
            url=f"http://localhost:8000/api/v1/benchmarks/{BENCH_ID}",
            json=_ok({"id": BENCH_ID, "project_id": PROJECT_ID, "state": "draft", "name": "X"}),
        )
        client = _client()
        client.update_benchmark(BENCH_ID, objective="only objective")
        request = httpx_mock.get_request()
        assert request is not None
        payload = request.read().decode()
        assert '"objective":"only objective"' in payload
        assert '"name"' not in payload
        client.close()


class TestDeleteBenchmark:
    def test_delete_benchmark_204(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="DELETE",
            url=f"http://localhost:8000/api/v1/benchmarks/{BENCH_ID}",
            status_code=204,
        )
        client = _client()
        client.delete_benchmark(BENCH_ID)  # should not raise
        client.close()


class TestCreateBenchmarkVersion:
    def test_create_benchmark_version(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/benchmarks/{BENCH_ID}/versions",
            json=_ok(
                {
                    "id": VERSION_ID,
                    "benchmark_id": BENCH_ID,
                    "version_string": "1.0.0",
                    "state": "draft",
                    "dataset_version_ids": [],
                    "evaluation_strategy_id": None,
                }
            ),
            status_code=201,
        )
        client = _client()
        version = client.create_benchmark_version(BENCH_ID, version_string="1.0.0")
        assert str(version.id) == VERSION_ID
        assert version.version_string == "1.0.0"
        client.close()


class TestPublishAndArchive:
    def test_publish_version(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/benchmark-versions/{VERSION_ID}/publish",
            json=_ok(None),
        )
        client = _client()
        client.publish_benchmark_version(VERSION_ID)  # should not raise
        client.close()

    def test_archive_version(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/benchmark-versions/{VERSION_ID}/archive",
            json=_ok(None),
        )
        client = _client()
        client.archive_benchmark_version(VERSION_ID)  # should not raise
        client.close()


class TestDiscovery:
    def test_list_organizations(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:8000/api/v1/organizations",
            json=_ok(
                [
                    {"id": ORG_ID, "name": "Test Org", "slug": "test-org", "display_name": None},
                ]
            ),
        )
        client = _client()
        orgs = client.list_organizations()
        assert len(orgs) == 1
        assert str(orgs[0].id) == ORG_ID
        assert orgs[0].name == "Test Org"
        client.close()

    def test_list_projects(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/organizations/{ORG_ID}/projects",
            json=_ok(
                [
                    {
                        "id": PROJECT_ID,
                        "name": "Test Project",
                        "slug": "test-project",
                        "description": None,
                        "org_id": ORG_ID,
                    }
                ]
            ),
        )
        client = _client()
        projects = client.list_projects(ORG_ID)
        assert len(projects) == 1
        assert str(projects[0].id) == PROJECT_ID
        assert projects[0].name == "Test Project"
        client.close()
