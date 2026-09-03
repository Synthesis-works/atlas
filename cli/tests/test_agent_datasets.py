"""Tests for the CLI dataset-authoring agent tools (v3.3).

Covers registration, the READ tools, the WRITE authoring tools, and the
registry's write classification (single-confirm, non-destructive).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from atlas_sdk.models.datasets import (
    DatasetRead,
    DatasetValidationResult,
    DatasetVersionRead,
)

from cli.agent.repl import AgentREPL
from cli.agent.tools.registry import ToolRegistry


def _uuid(n: int) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-0000-0000-0000000000{n:02d}")


PROJECT = str(_uuid(10))
DATASET = str(_uuid(11))
VERSION = str(_uuid(12))


def _dataset(name: str = "My Dataset") -> DatasetRead:
    return DatasetRead(
        id=_uuid(11),
        project_id=_uuid(10),
        created_by_member_id=None,
        status="active",
        created_at="2026-07-16T12:00:00Z",
        updated_at="2026-07-16T12:00:00Z",
        name=name,
        description=None,
        versions=[
            DatasetVersionRead(
                id=_uuid(12),
                dataset_id=_uuid(11),
                version_string="v1.0.0",
                storage_path="p",
                lifecycle="uploaded",
                version_number=1,
                created_at="2026-07-16T12:00:00Z",
            )
        ],
        total_tasks=1,
        sample_tasks=[{"name": "task_0", "input": {"a": 1}, "expected_output": {"b": 2}}],
    )


def _mock_client() -> MagicMock:
    mock = MagicMock()
    mock.list_datasets.return_value = [_dataset()]
    mock.get_dataset.return_value = _dataset()
    mock.create_dataset.return_value = _dataset("Created Dataset")
    mock.update_dataset.return_value = _dataset("Renamed Dataset")
    mock.upload_dataset_tasks.return_value = DatasetVersionRead(
        id=_uuid(12),
        dataset_id=_uuid(11),
        version_string="v2.0.0",
        storage_path="p",
        lifecycle="uploaded",
        version_number=2,
        created_at="2026-07-16T12:00:00Z",
    )
    mock.validate_dataset.return_value = DatasetValidationResult(
        dataset_id=_uuid(11),
        version_id=_uuid(12),
        lifecycle="valid",
        valid=True,
        task_count=1,
        messages=["Dataset schema is valid."],
    )
    return mock


class TestDatasetToolsRegistered:
    def test_dataset_tools_present(self) -> None:
        reg = ToolRegistry()
        names = set(reg.registry.keys())
        for expected in {
            "list_datasets",
            "get_dataset",
            "create_dataset",
            "update_dataset",
            "upload_dataset_tasks",
            "validate_dataset",
        }:
            assert expected in names

    def test_write_and_non_destructive_classification(self) -> None:
        reg = ToolRegistry()
        for name in {
            "create_dataset",
            "update_dataset",
            "upload_dataset_tasks",
            "validate_dataset",
        }:
            assert reg.is_mutating(name) is True, name
            assert reg.is_destructive(name) is False, name
        for name in {"list_datasets", "get_dataset"}:
            assert reg.is_mutating(name) is False, name


class TestListDatasetsTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("list_datasets", client, {"project_id": PROJECT})
        client.list_datasets.assert_called_once_with(PROJECT)
        assert result.ok is True
        assert "My Dataset" in result.summary

    def test_missing_project_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("list_datasets", _mock_client(), {})
        assert result.ok is False
        assert result.error


class TestGetDatasetTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("get_dataset", client, {"project_id": PROJECT, "dataset_id": DATASET})
        client.get_dataset.assert_called_once_with(PROJECT, DATASET)
        assert result.ok is True
        assert DATASET in result.summary

    def test_missing_id_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("get_dataset", _mock_client(), {"project_id": PROJECT})
        assert result.ok is False
        assert result.error


class TestCreateDatasetTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "create_dataset",
            client,
            {"project_id": PROJECT, "name": "Created Dataset"},
        )
        client.create_dataset.assert_called_once_with(
            PROJECT,
            name="Created Dataset",
            description=None,
            version_string="v1.0.0",
            tasks=None,
        )
        assert result.ok is True
        assert DATASET in result.summary

    def test_delegates_with_tasks(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "create_dataset",
            client,
            {
                "project_id": PROJECT,
                "name": "Created Dataset",
                "tasks": [{"input": {"q": 1}, "expected_output": {"a": 2}, "description": "d"}],
            },
        )
        _, kwargs = client.create_dataset.call_args
        assert kwargs["tasks"] == [
            {"input": {"q": 1}, "expected_output": {"a": 2}, "description": "d"}
        ]
        assert result.ok is True

    def test_missing_name_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("create_dataset", _mock_client(), {"project_id": PROJECT})
        assert result.ok is False
        assert result.error


class TestUpdateDatasetTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "update_dataset",
            client,
            {"project_id": PROJECT, "dataset_id": DATASET, "name": "Renamed Dataset"},
        )
        client.update_dataset.assert_called_once_with(
            PROJECT, DATASET, name="Renamed Dataset", description=None
        )
        assert result.ok is True
        assert "Renamed Dataset" in result.summary

    def test_no_fields_is_noop(self) -> None:
        reg = ToolRegistry()
        result = reg.execute(
            "update_dataset", _mock_client(), {"project_id": PROJECT, "dataset_id": DATASET}
        )
        assert result.ok is False
        assert "no fields" in result.summary


class TestUploadTasksTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "upload_dataset_tasks",
            client,
            {
                "project_id": PROJECT,
                "dataset_id": DATASET,
                "version_string": "v2.0.0",
                "tasks": [{"input": {"q": 1}, "expected_output": {"a": 2}}],
            },
        )
        client.upload_dataset_tasks.assert_called_once_with(
            PROJECT,
            DATASET,
            [{"input": {"q": 1}, "expected_output": {"a": 2}}],
            version_string="v2.0.0",
        )
        assert result.ok is True
        assert VERSION in result.summary

    def test_empty_tasks_is_noop(self) -> None:
        reg = ToolRegistry()
        result = reg.execute(
            "upload_dataset_tasks",
            _mock_client(),
            {"project_id": PROJECT, "dataset_id": DATASET, "tasks": []},
        )
        assert result.ok is False
        assert "no tasks" in result.summary


class TestValidateDatasetTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "validate_dataset", client, {"project_id": PROJECT, "dataset_id": DATASET}
        )
        client.validate_dataset.assert_called_once_with(PROJECT, DATASET)
        assert result.ok is True
        assert "VALID" in result.summary

    def test_missing_id_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("validate_dataset", _mock_client(), {"project_id": PROJECT})
        assert result.ok is False
        assert result.error


class TestDatasetWriteConfirms:
    def test_dataset_write_tools_prompt_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[bool] = []

        def fake_confirm(_msg: str, default: bool = False) -> bool:
            calls.append(default)
            return True

        monkeypatch.setattr("cli.agent.repl.click.confirm", fake_confirm)
        provider = MagicMock()
        provider.generate.return_value = MagicMock(content="", function_calls=[], text="done")
        repl = AgentREPL(
            provider=provider,
            client=_mock_client(),
            registry=ToolRegistry(),
            confirm=None,
            echo=lambda s: None,
        )
        assert (
            repl._prompt_confirm("create_dataset", {"project_id": PROJECT, "name": "X"}) is True
        )
        assert len(calls) == 1
