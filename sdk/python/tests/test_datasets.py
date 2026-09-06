"""Tests for the AtlasClient dataset methods (v3.3).

The dataset endpoints return bare (non-``APIResponse``) payloads, so the
mocked responses are the raw ``DatasetRead``/``DatasetVersionRead``/
``DatasetValidationResult`` shapes.  Uses ``pytest-httpx``; no live Atlas
deployment required.
"""

from __future__ import annotations

import pytest

from atlas_sdk.auth import StaticTokenSupplier
from atlas_sdk.client import AtlasClient

PROJECT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DATASET_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
VERSION_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _dataset(ds_id: str = DATASET_ID) -> dict:
    return {
        "id": ds_id,
        "project_id": PROJECT_ID,
        "created_by_member_id": None,
        "status": "active",
        "created_at": "2026-07-16T12:00:00Z",
        "updated_at": "2026-07-16T12:00:00Z",
        "name": "MMLU-Pro Test Set",
        "description": "A dataset",
        "registry_id": None,
        "source_id": None,
        "license_id": None,
        "versions": [
            {
                "id": VERSION_ID,
                "dataset_id": ds_id,
                "version_string": "v1.0.0",
                "storage_path": f"datasets/{ds_id}/v1.0.0",
                "checksum": None,
                "schema_def": None,
                "lifecycle": "uploaded",
                "version_number": 1,
                "created_at": "2026-07-16T12:00:00Z",
                "created_by_id": None,
            }
        ],
        "total_tasks": 1,
        "sample_tasks": [{"name": "task_0", "input": {"text": "hi"}, "expected_output": {"a": 1}}],
    }


def _client() -> AtlasClient:
    return AtlasClient("http://localhost:8000", token_supplier=StaticTokenSupplier("t"))


class TestListDatasets:
    def test_list_datasets(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets",
            json=[_dataset()],
        )
        client = _client()
        datasets = client.list_datasets(PROJECT_ID)
        assert len(datasets) == 1
        assert str(datasets[0].id) == DATASET_ID
        assert datasets[0].name == "MMLU-Pro Test Set"
        client.close()


class TestGetDataset:
    def test_get_dataset(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="GET",
            url=(f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets/{DATASET_ID}"),
            json=_dataset(),
        )
        client = _client()
        ds = client.get_dataset(PROJECT_ID, DATASET_ID)
        assert str(ds.id) == DATASET_ID
        assert ds.total_tasks == 1
        assert ds.versions is not None and len(ds.versions) == 1
        client.close()


class TestCreateDataset:
    def test_create_dataset(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets",
            json=_dataset(),
            status_code=201,
        )
        client = _client()
        ds = client.create_dataset(PROJECT_ID, name="MMLU-Pro Test Set")
        assert str(ds.id) == DATASET_ID
        client.close()

    def test_create_sends_tasks(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets",
            json=_dataset(),
            status_code=201,
        )
        client = _client()
        client.create_dataset(
            PROJECT_ID,
            name="X",
            description="d",
            version_string="v2.0.0",
            tasks=[{"input": {"t": 1}, "expected_output": {"o": 2}}],
        )
        request = httpx_mock.get_request()
        assert request is not None
        payload = request.read().decode()
        assert '"name":"X"' in payload
        assert '"version_string":"v2.0.0"' in payload
        assert '"expected_output"' in payload
        client.close()


class TestUpdateDataset:
    def test_update_dataset(self, httpx_mock: pytest.MockTransport) -> None:
        updated = _dataset()
        updated["name"] = "Renamed"
        httpx_mock.add_response(
            method="PUT",
            url=(f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets/{DATASET_ID}"),
            json=updated,
        )
        client = _client()
        ds = client.update_dataset(PROJECT_ID, DATASET_ID, name="Renamed")
        assert ds.name == "Renamed"
        client.close()

    def test_update_only_provided(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="PUT",
            url=(f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets/{DATASET_ID}"),
            json=_dataset(),
        )
        client = _client()
        client.update_dataset(PROJECT_ID, DATASET_ID, description="only desc")
        request = httpx_mock.get_request()
        assert request is not None
        payload = request.read().decode()
        assert '"description":"only desc"' in payload
        assert '"name"' not in payload
        client.close()


class TestUploadTasks:
    def test_upload_tasks(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=(f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets/{DATASET_ID}/tasks"),
            json={
                "id": VERSION_ID,
                "dataset_id": DATASET_ID,
                "version_string": "v1.0.0",
                "storage_path": f"datasets/{DATASET_ID}/v1.0.0",
                "checksum": None,
                "schema_def": None,
                "lifecycle": "uploaded",
                "version_number": 1,
                "created_at": "2026-07-16T12:00:00Z",
                "created_by_id": None,
            },
            status_code=201,
        )
        client = _client()
        version = client.upload_dataset_tasks(
            PROJECT_ID,
            DATASET_ID,
            [{"input": {"t": 1}, "expected_output": {"o": 2}}],
        )
        assert str(version.id) == VERSION_ID
        client.close()


class TestValidateDataset:
    def test_validate(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=(
                f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets/{DATASET_ID}/validate"
            ),
            json={
                "dataset_id": DATASET_ID,
                "version_id": VERSION_ID,
                "lifecycle": "valid",
                "valid": True,
                "task_count": 2,
                "messages": ["Dataset schema is valid."],
            },
        )
        client = _client()
        result = client.validate_dataset(PROJECT_ID, DATASET_ID)
        assert result.valid is True
        assert result.task_count == 2
        assert result.lifecycle == "valid"
        client.close()

    def test_validate_not_found(self, httpx_mock: pytest.MockTransport) -> None:
        httpx_mock.add_response(
            method="POST",
            url=(
                f"http://localhost:8000/api/v1/projects/{PROJECT_ID}/datasets/{DATASET_ID}/validate"
            ),
            json={"detail": "Dataset not found"},
            status_code=404,
        )
        from atlas_sdk.errors import NotFoundError

        client = _client()
        with pytest.raises(NotFoundError):
            client.validate_dataset(PROJECT_ID, DATASET_ID)
        client.close()
