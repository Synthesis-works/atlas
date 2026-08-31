"""Tests for ``--json-schema`` (Slice 6).

The flag prints the JSON Schema document describing the command's JSON
output, resolved **offline** from the SDK pydantic model — never from the
backend.  Supported commands are those whose JSON output is a faithful
pydantic model dump; every other command must reject the flag (exit 2).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from atlas_sdk import (
    BenchmarkRead,
    DashboardSnapshot,
    ExecutionResponse,
    LeaderboardRead,
    ModelBenchmarkHistory,
    ModelSummary,
    ReportSummaryRead,
    TrendPoint,
)
from click.testing import CliRunner

from cli.app import main
from cli.output.schema import ArraySchemaDocument, SchemaDocument

_UUID = "00000000-0000-0000-0000-000000000000"
_BV = "181d1c91-15f9-43e7-866d-33809aaaedf1"
_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def _schema(runner: CliRunner, args: list[str]) -> dict:
    result = runner.invoke(main, args)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


# --- helper unit tests ------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "field", "nested"),
    [
        (BenchmarkRead, "id", False),
        (DashboardSnapshot, "summary", True),
        (ExecutionResponse, "attempts", True),
        (ReportSummaryRead, "scores", True),
        (LeaderboardRead, "entries", True),
        (ModelSummary, "benchmarks", False),
    ],
)
def test_schema_document_adds_dialect(model: type, field: str, nested: bool) -> None:
    doc = SchemaDocument(model)
    assert doc["$schema"] == _DIALECT
    assert doc["type"] == "object"
    assert field in doc["properties"]
    assert ("$defs" in doc) is nested


@pytest.mark.parametrize(
    "model",
    [TrendPoint, ModelBenchmarkHistory],
)
def test_array_schema_document_wraps_items(model: type) -> None:
    doc = ArraySchemaDocument(model)
    assert doc["$schema"] == _DIALECT
    assert doc["type"] == "array"
    assert doc["items"]["type"] == "object"
    assert "$schema" not in doc["items"]


# --- offline emission per command -------------------------------------------


def test_dashboard_json_schema_offline(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient") as mock_client:
        schema = _schema(runner, ["dashboard", "--json-schema"])
    mock_client.assert_not_called()
    assert {"generated_at", "version", "summary", "running_jobs", "activity"} <= set(
        schema["properties"]
    )
    summary = schema["$defs"]["DashboardSummary"]["properties"]
    assert summary["total_runs_count"]["type"] == "integer"


def test_run_get_json_schema_offline(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient") as mock_client:
        schema = _schema(runner, ["run", "get", _UUID, "--json-schema"])
    mock_client.assert_not_called()
    props = schema["properties"]
    assert {"status", "target_model", "total_items", "attempts"} <= set(props)
    assert "ExecutionAttemptResponse" in schema["$defs"]


def test_report_get_json_schema_nested_scores(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient") as mock_client:
        schema = _schema(runner, ["report", "get", _UUID, "--json-schema"])
    mock_client.assert_not_called()
    props = schema["properties"]
    assert {"run_id", "benchmark_name", "overall_score", "scores"} <= set(props)
    cap = schema["$defs"]["CapabilityScoreRead"]["properties"]
    assert {"capability_name", "score"} == set(cap)


def test_leaderboard_benchmark_json_schema(runner: CliRunner) -> None:
    schema = _schema(runner, ["leaderboard", "benchmark", _BV, "--json-schema"])
    assert {"leaderboard_type", "title", "entries"} <= set(schema["properties"])
    entry = schema["$defs"]["LeaderboardEntryRead"]["properties"]
    assert {"rank", "model_name", "overall_score", "benchmark_count"} <= set(entry)


def test_leaderboard_model_json_schema(runner: CliRunner) -> None:
    schema = _schema(runner, ["leaderboard", "model", "mock", "--json-schema"])
    assert {"model", "benchmarks", "average_score", "best_rank"} <= set(
        schema["properties"]
    )


def test_leaderboard_model_history_is_array_schema(runner: CliRunner) -> None:
    schema = _schema(runner, ["leaderboard", "model", "mock", "--history", "--json-schema"])
    assert schema["type"] == "array"
    items = schema["items"]["properties"]
    assert {"timestamp", "score", "execution_id"} <= set(items)


def test_leaderboard_model_benchmarks_is_array_schema(runner: CliRunner) -> None:
    schema = _schema(
        runner, ["leaderboard", "model", "mock", "--benchmarks", "--json-schema"]
    )
    assert schema["type"] == "array"
    assert "benchmark_name" in schema["items"]["properties"]


def test_benchmark_list_json_schema(runner: CliRunner) -> None:
    schema = _schema(runner, ["benchmark", "list", "--json-schema"])
    assert {"items", "total", "limit", "offset", "next_cursor"} <= set(
        schema["properties"]
    )
    assert schema["$defs"]["BenchmarkRead"]["properties"]["name"]["type"] == "string"


def test_benchmark_get_json_schema(runner: CliRunner) -> None:
    schema = _schema(runner, ["benchmark", "get", _UUID, "--json-schema"])
    assert {"id", "project_id", "state", "name"} == set(schema["properties"])


# --- flag semantics ----------------------------------------------------------


def test_json_schema_is_deterministic(runner: CliRunner) -> None:
    first = json.dumps(_schema(runner, ["dashboard", "--json-schema"]))
    second = json.dumps(_schema(runner, ["dashboard", "--json-schema"]))
    assert first == second


def test_json_schema_agrees_across_output_modes(runner: CliRunner) -> None:
    human = _schema(runner, ["dashboard", "--json-schema"])
    via_json = _schema(runner, ["--output", "json", "dashboard", "--json-schema"])
    assert human == via_json


def test_json_schema_with_quiet_is_silent(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient") as mock_client:
        result = runner.invoke(main, ["--quiet", "dashboard", "--json-schema"])
    mock_client.assert_not_called()
    assert result.exit_code == 0
    assert result.output == ""


@pytest.mark.parametrize(
    "args",
    [
        ["activity", "--json-schema"],
        ["run", "list", "--json-schema"],
        ["run", "cancel", _UUID, "--json-schema"],
        ["report", "list", "--json-schema"],
        ["report", "export", _UUID, "--json-schema"],
        ["benchmark", "versions", _BV, "--json-schema"],
    ],
)
def test_excluded_commands_reject_json_schema(runner: CliRunner, args: list[str]) -> None:
    result = runner.invoke(main, args)
    assert result.exit_code == 2
    assert "no such option" in result.output.lower()


@pytest.mark.parametrize(
    "args",
    [
        ["dashboard", "--help"],
        ["run", "get", "--help"],
        ["report", "get", "--help"],
        ["leaderboard", "model", "--help"],
        ["benchmark", "get", "--help"],
    ],
)
def test_help_lists_json_schema_flag(runner: CliRunner, args: list[str]) -> None:
    result = runner.invoke(main, args)
    assert result.exit_code == 0
    assert "--json-schema" in result.output
