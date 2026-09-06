"""Tests for `atlas model list` (Slice 7).

Mocks at the SDK boundary to test CLI rendering without real HTTP.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from atlas_sdk import ModelRead, ModelStatus
from click.testing import CliRunner

from cli.app import main


def _model(
    id: str,
    provider: str,
    *,
    status: ModelStatus = ModelStatus.AVAILABLE,
    is_test_only: bool = False,
) -> ModelRead:
    return ModelRead(
        id=id,
        provider=provider,
        display_name=id.split("/")[-1],
        status=status,
        is_test_only=is_test_only,
    )


def _mock_client(models: list[ModelRead] | None = None) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_models.return_value = models or [
        _model("mock", "mock", is_test_only=True),
        _model("groq/llama-3.1-8b-instant", "groq", status=ModelStatus.NOT_CONFIGURED),
    ]
    return mock


def _mock_client_empty() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_models.return_value = []
    return mock


def _mock_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_models.side_effect = exc
    return mock


# ── discovery ───────────────────────────────────────────────────────────


def test_model_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "model" in result.output.lower()


def test_model_list_in_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["model", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output.lower()


# ── human mode ──────────────────────────────────────────────────────────


def test_model_list_human(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["model", "list"])
    assert result.exit_code == 0
    assert "mock" in result.output
    assert "groq/llama-3.1-8b-instant" in result.output
    assert "groq" in result.output
    assert "NOT_CONFIGURED" in result.output


def test_model_list_human_title(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()) as mock_cls:
        result = runner.invoke(main, ["model", "list"])
    assert result.exit_code == 0
    assert "Available Models" in result.output
    mock_cls.return_value.list_models.assert_called_once_with()


# ── json mode ───────────────────────────────────────────────────────────


def test_model_list_json(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--output", "json", "model", "list"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert payload[0]["id"] == "mock"
    assert payload[0]["status"] == "AVAILABLE"
    assert payload[0]["is_test_only"] is True
    assert payload[1]["status"] == "NOT_CONFIGURED"


# ── quiet mode ──────────────────────────────────────────────────────────


def test_model_list_quiet_is_silent(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client()):
        result = runner.invoke(main, ["--quiet", "model", "list"])
    assert result.exit_code == 0
    assert result.output == ""


def test_model_list_quiet_error_is_reported(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client_error(RuntimeError("boom"))):
        result = runner.invoke(main, ["--quiet", "model", "list"])
    assert result.exit_code == 1
    assert "boom" in result.output


# ── empty & error paths ─────────────────────────────────────────────────


def test_model_list_empty(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client_empty()):
        result = runner.invoke(main, ["model", "list"])
    assert result.exit_code == 0
    assert "no models" in result.output.lower()


def test_model_list_error_human(runner: CliRunner) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_client_error(RuntimeError("boom"))):
        result = runner.invoke(main, ["model", "list"])
    assert result.exit_code == 1
    assert "boom" in result.output
