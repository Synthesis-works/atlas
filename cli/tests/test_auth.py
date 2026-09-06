"""Tests for `atlas login` and `atlas logout`.

Mock the SDK boundary (``AtlasClient``) so no live backend is required.
Each test is isolated from the real user config dir by the autouse
``_isolate_cli_config`` fixture in ``conftest.py``: ``APPDATA`` points at
the test's ``tmp_path``, so the saved profile lands at
``tmp_path/Atlas/config.toml``.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from atlas_sdk.errors import AuthError
from atlas_sdk.models.auth import TokenResponse
from click.testing import CliRunner

from cli.app import main
from cli.config import load_config, save_profile


def _profile_path(tmp_path: Path) -> Path:
    return tmp_path / "Atlas" / "config.toml"


def _mock_login_client(token: str = "expected-token") -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.login.return_value = TokenResponse(access_token=token)
    return mock


def _mock_login_client_error(exc: Exception) -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.login.side_effect = exc
    return mock


# ── login ────────────────────────────────────────────────────────────────


def test_login_success_persists_token(runner: CliRunner, tmp_path: Path) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_login_client()):
        result = runner.invoke(main, ["login"], input="demo@atlas.val\npassword123\n")
    assert result.exit_code == 0
    assert "Logged in" in result.output
    assert "expected-token" not in result.output
    cfg = load_config(config_path=_profile_path(tmp_path))
    assert cfg.token == "expected-token"
    assert cfg.base_url == "http://localhost:8000"


def test_login_email_flag_prompts_only_for_password(runner: CliRunner, tmp_path: Path) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_login_client()):
        result = runner.invoke(main, ["login", "--email", "demo@atlas.val"], input="password123\n")
    assert result.exit_code == 0
    assert "Email:" not in result.output
    cfg = load_config(config_path=_profile_path(tmp_path))
    assert cfg.token == "expected-token"


def test_login_password_stdin_success(runner: CliRunner, tmp_path: Path) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_login_client()):
        result = runner.invoke(
            main,
            ["login", "--email", "demo@atlas.val", "--password-stdin"],
            input="password123\n",
        )
    assert result.exit_code == 0
    cfg = load_config(config_path=_profile_path(tmp_path))
    assert cfg.token == "expected-token"


def test_login_password_stdin_empty_is_validation_error(runner: CliRunner, tmp_path: Path) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_login_client()):
        result = runner.invoke(
            main,
            ["login", "--email", "demo@atlas.val", "--password-stdin"],
            input="",
        )
    assert result.exit_code == 7
    cfg = load_config(config_path=_profile_path(tmp_path))
    assert cfg.token is None


def test_login_json_payload_never_contains_token(runner: CliRunner, tmp_path: Path) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_login_client("secret-token")):
        result = runner.invoke(
            main,
            [
                "--output",
                "json",
                "login",
                "--email",
                "demo@atlas.val",
                "--password-stdin",
            ],
            input="password123\n",
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["email"] == "demo@atlas.val"
    assert data["base_url"] == "http://localhost:8000"
    assert "token" not in json.dumps(data)
    assert "secret-token" not in result.output


def test_login_quiet_emits_no_stdout(runner: CliRunner, tmp_path: Path) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_login_client()):
        result = runner.invoke(
            main,
            ["--quiet", "login", "--email", "demo@atlas.val", "--password-stdin"],
            input="password123\n",
        )
    assert result.exit_code == 0
    assert result.output == ""
    assert load_config(config_path=_profile_path(tmp_path)).token == "expected-token"


def test_login_invalid_credentials_exits_auth_code(runner: CliRunner, tmp_path: Path) -> None:
    err = AuthError(status=401, message="Invalid credentials")
    with patch("cli.client.AtlasClient", return_value=_mock_login_client_error(err)):
        result = runner.invoke(main, ["login"], input="demo@atlas.val\nwrongpass\n")
    assert result.exit_code == 3
    assert load_config(config_path=_profile_path(tmp_path)).token is None


def test_login_invalid_credentials_json(runner: CliRunner, tmp_path: Path) -> None:
    err = AuthError(status=401, message="Invalid credentials")
    with patch("cli.client.AtlasClient", return_value=_mock_login_client_error(err)):
        result = runner.invoke(
            main,
            ["--output", "json", "login", "--email", "demo@atlas.val", "--password-stdin"],
            input="wrongpass\n",
        )
    assert result.exit_code == 3
    parsed = json.loads(result.output)
    assert parsed["error"]["status"] == 401
    assert load_config(config_path=_profile_path(tmp_path)).token is None


def test_login_saves_active_base_url(runner: CliRunner, tmp_path: Path) -> None:
    with patch("cli.client.AtlasClient", return_value=_mock_login_client()):
        result = runner.invoke(
            main,
            ["--base-url", "http://saved:9000", "login"],
            input="demo@atlas.val\npassword123\n",
        )
    assert result.exit_code == 0
    cfg = load_config(config_path=_profile_path(tmp_path))
    assert cfg.base_url == "http://saved:9000"
    assert cfg.token == "expected-token"


# ── logout ───────────────────────────────────────────────────────────────


def test_logout_removes_saved_token(runner: CliRunner, tmp_path: Path) -> None:
    save_profile(
        token="saved-token",
        base_url="http://localhost:8000",
        config_path=_profile_path(tmp_path),
    )
    result = runner.invoke(main, ["logout"])
    assert result.exit_code == 0
    cfg = load_config(config_path=_profile_path(tmp_path))
    assert cfg.token is None
    assert cfg.base_url == "http://localhost:8000"


def test_logout_succeeds_when_no_saved_token_exists(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(main, ["logout"])
    assert result.exit_code == 0
    assert "Logged out" in result.output


def test_logout_honors_json_output(runner: CliRunner, tmp_path: Path) -> None:
    save_profile(
        token="saved-token",
        base_url="http://localhost:8000",
        config_path=_profile_path(tmp_path),
    )
    result = runner.invoke(main, ["--output", "json", "logout"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert "saved-token" not in result.output


def test_logout_honors_quiet_output(runner: CliRunner, tmp_path: Path) -> None:
    save_profile(
        token="saved-token",
        base_url="http://localhost:8000",
        config_path=_profile_path(tmp_path),
    )
    result = runner.invoke(main, ["--quiet", "logout"])
    assert result.exit_code == 0
    assert result.output == ""
