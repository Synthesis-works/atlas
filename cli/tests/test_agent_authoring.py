"""Tests for the CLI benchmark-authoring agent tools (v3.2).

Covers the discovery (READ) tools, authoring (WRITE) tools, the registry's
write/destructive classification, and the REPL double-confirm for destructive
operations.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from atlas_sdk.models.benchmarks import BenchmarkRead, BenchmarkVersionRead
from atlas_sdk.models.projects import OrganizationRead, ProjectRead

from cli.agent.repl import AgentREPL
from cli.agent.tools.registry import ToolRegistry


def _uuid(n: int) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-0000-0000-0000000000{n:02d}")


PROJECT = str(_uuid(1))
BENCH = str(_uuid(2))
VERSION = str(_uuid(3))
ORG = str(_uuid(4))


def _mock_client() -> MagicMock:
    mock = MagicMock()
    mock.create_benchmark.return_value = BenchmarkRead(
        id=_uuid(2), project_id=_uuid(1), state="draft", name="New Bench"
    )
    mock.update_benchmark.return_value = BenchmarkRead(
        id=_uuid(2), project_id=_uuid(1), state="draft", name="Renamed"
    )
    mock.create_benchmark_version.return_value = BenchmarkVersionRead(
        id=_uuid(3), benchmark_id=_uuid(2), version_string="1.0.0", state="draft"
    )
    mock.list_organizations.return_value = [
        OrganizationRead(id=_uuid(4), name="Test Org", slug="test-org")
    ]
    mock.list_projects.return_value = [
        ProjectRead(id=_uuid(1), name="Test Project", slug="test-project")
    ]
    return mock


def _repl_with(provider: MagicMock, echo=None) -> AgentREPL:
    return AgentREPL(
        provider=provider,
        client=_mock_client(),
        confirm=lambda tool, args: True,
        echo=echo or (lambda s: None),
    )


class TestAuthoringToolsRegistered:
    def test_authoring_and_discovery_tools_present(self) -> None:
        reg = ToolRegistry()
        names = set(reg.registry.keys())
        for expected in {
            "create_benchmark",
            "update_benchmark",
            "delete_benchmark",
            "create_benchmark_version",
            "publish_benchmark_version",
            "archive_benchmark_version",
            "list_organizations",
            "list_projects",
        }:
            assert expected in names

    def test_write_and_destructive_classification(self) -> None:
        reg = ToolRegistry()
        # WRITE mutations prompt
        for name in {
            "create_benchmark",
            "update_benchmark",
            "create_benchmark_version",
            "publish_benchmark_version",
            "archive_benchmark_version",
            "delete_benchmark",
            "submit_run",
        }:
            assert reg.is_mutating(name) is True, name
        # READ discovery never prompts
        for name in {"list_organizations", "list_projects", "list_benchmarks"}:
            assert reg.is_mutating(name) is False, name
        # destructive ops get the stronger classification
        assert reg.is_destructive("delete_benchmark") is True
        assert reg.is_destructive("archive_benchmark_version") is True
        assert reg.is_destructive("create_benchmark") is False
        assert reg.is_destructive("publish_benchmark_version") is False
        assert reg.is_destructive("submit_run") is False
        assert reg.is_destructive("list_benchmarks") is False


class TestCreateBenchmarkTool:
    def test_delegates_and_returns_id(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "create_benchmark", client, {"project_id": PROJECT, "name": "New Bench"}
        )
        client.create_benchmark.assert_called_once_with(
            PROJECT, name="New Bench", objective=None,
            category_ids=None, capability_ids=None,
        )
        assert result.ok is True
        assert BENCH in result.summary

    def test_missing_name_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("create_benchmark", _mock_client(), {"project_id": PROJECT})
        assert result.ok is False
        assert result.error


class TestUpdateBenchmarkTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "update_benchmark", client, {"benchmark_id": BENCH, "name": "Renamed"}
        )
        client.update_benchmark.assert_called_once()
        assert result.ok is True
        assert "Renamed" in result.summary

    def test_no_fields_is_noop_failure(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("update_benchmark", _mock_client(), {"benchmark_id": BENCH})
        assert result.ok is False
        assert "no fields" in result.summary

    def test_missing_id_fails(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("update_benchmark", _mock_client(), {})
        assert result.ok is False
        assert result.error


class TestCreateBenchmarkVersionTool:
    def test_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(
            "create_benchmark_version",
            client,
            {"benchmark_id": BENCH, "version_string": "1.0.0"},
        )
        client.create_benchmark_version.assert_called_once_with(
            BENCH, version_string="1.0.0",
            dataset_version_ids=None, evaluation_strategy_id=None,
        )
        assert result.ok is True
        assert VERSION in result.summary


@pytest.mark.parametrize(
    "tool,args",
    [
        ("publish_benchmark_version", {"version_id": VERSION}),
        ("archive_benchmark_version", {"version_id": VERSION}),
        ("delete_benchmark", {"benchmark_id": BENCH}),
    ],
)
class TestStateChangeTools:
    def test_delegates(self, tool: str, args: dict) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute(tool, client, args)
        assert result.ok is True
        assert result.summary

    def test_missing_id_fails(self, tool: str, args: dict) -> None:
        reg = ToolRegistry()
        result = reg.execute(tool, _mock_client(), {})
        assert result.ok is False
        assert result.error


class TestDiscoveryTools:
    def test_list_organizations_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("list_organizations", client, {})
        client.list_organizations.assert_called_once()
        assert result.ok is True

    def test_list_projects_delegates(self) -> None:
        reg = ToolRegistry()
        client = _mock_client()
        result = reg.execute("list_projects", client, {"org_id": ORG})
        client.list_projects.assert_called_once_with(ORG)
        assert result.ok is True

    def test_list_projects_requires_org(self) -> None:
        reg = ToolRegistry()
        result = reg.execute("list_projects", _mock_client(), {})
        assert result.ok is False


class TestDestructiveDoubleConfirm:
    def test_destructive_prompts_twice(self, monkeypatch: pytest.MonkeyPatch) -> None:
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
            confirm=None,  # use the built-in _prompt_confirm
            echo=lambda s: None,
        )
        assert repl._prompt_confirm("delete_benchmark", {"benchmark_id": BENCH}) is True
        assert len(calls) == 2  # two confirm prompts for a destructive op

    def test_non_destructive_prompts_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[bool] = []

        def fake_confirm(_msg: str, default: bool = False) -> bool:
            calls.append(default)
            return True

        monkeypatch.setattr("cli.agent.repl.click.confirm", fake_confirm)
        repl = AgentREPL(
            provider=MagicMock(),
            client=_mock_client(),
            registry=ToolRegistry(),
            confirm=None,
            echo=lambda s: None,
        )
        assert (
            repl._prompt_confirm("create_benchmark", {"project_id": PROJECT, "name": "X"})
            is True
        )
        assert len(calls) == 1

    def test_destructive_first_decline_stops(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[bool] = []
        answers = iter([False])

        def fake_confirm(_msg: str, default: bool = False) -> bool:
            calls.append(default)
            return next(answers)

        monkeypatch.setattr("cli.agent.repl.click.confirm", fake_confirm)
        repl = AgentREPL(
            provider=MagicMock(),
            client=_mock_client(),
            registry=ToolRegistry(),
            confirm=None,
            echo=lambda s: None,
        )
        assert repl._prompt_confirm("delete_benchmark", {"benchmark_id": BENCH}) is False
        assert len(calls) == 1
