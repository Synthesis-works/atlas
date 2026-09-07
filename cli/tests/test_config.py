"""Tests for config precedence — CLI flags > env vars > profile > defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.config import clear_saved_token, default_config_path, load_config, save_profile


def test_defaults() -> None:
    cfg = load_config()
    assert cfg.base_url == "https://atlas-api-synthesis-works.vercel.app"
    assert cfg.timeout == 60.0
    assert cfg.output == "human"
    assert cfg.profile == "default"
    assert cfg.no_color is False
    assert cfg.quiet is False
    assert cfg.retries == 3


def test_fresh_install_defaults_to_hosted_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_BASE_URL", raising=False)
    monkeypatch.delenv("ATLAS_PROFILE", raising=False)
    cfg = load_config()
    assert cfg.base_url == "https://atlas-api-synthesis-works.vercel.app"


def test_localhost_override_still_works_via_flag() -> None:
    assert load_config(base_url="http://localhost:8000").base_url == "http://localhost:8000"


def test_localhost_override_still_works_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_BASE_URL", "http://localhost:8000")
    assert load_config().base_url == "http://localhost:8000"


def test_cli_flags_override() -> None:
    cfg = load_config(
        base_url="http://custom:9000",
        timeout=30.0,
        output="json",
        profile="staging",
        no_color=True,
        quiet=True,
    )
    assert cfg.base_url == "http://custom:9000"
    assert cfg.timeout == 30.0
    assert cfg.output == "json"
    assert cfg.profile == "staging"
    assert cfg.no_color is True
    assert cfg.quiet is True


def test_env_vars(monkeypatch: object) -> None:
    import pytest

    mp = pytest.MonkeyPatch()
    mp.setenv("ATLAS_BASE_URL", "http://env-host:7000")
    mp.setenv("ATLAS_TIMEOUT", "120")
    mp.setenv("ATLAS_PROFILE", "ci")
    mp.setenv("ATLAS_OUTPUT", "json")
    try:
        cfg = load_config()
        assert cfg.base_url == "http://env-host:7000"
        assert cfg.timeout == 120.0
        assert cfg.profile == "ci"
        assert cfg.output == "json"
    finally:
        mp.undo()


def test_cli_over_env(monkeypatch: object) -> None:
    import pytest

    mp = pytest.MonkeyPatch()
    mp.setenv("ATLAS_BASE_URL", "http://env-host:7000")
    try:
        cfg = load_config(base_url="http://flag-host:8000")
        assert cfg.base_url == "http://flag-host:8000"
    finally:
        mp.undo()


def test_invalid_timeout_falls_back_to_default(monkeypatch: object) -> None:
    import pytest

    mp = pytest.MonkeyPatch()
    mp.setenv("ATLAS_TIMEOUT", "not-a-number")
    try:
        cfg = load_config()
        assert cfg.timeout == 60.0
    finally:
        mp.undo()


def test_retries_from_cli_flag() -> None:
    assert load_config(retries=0).retries == 0
    assert load_config(retries=9).retries == 9


def test_retries_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_RETRIES", "5")
    assert load_config().retries == 5


def test_cli_flag_over_env_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_RETRIES", "5")
    assert load_config(retries=0).retries == 0


def test_invalid_retries_env_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATLAS_RETRIES", "not-a-number")
    assert load_config().retries == 3


def test_quiet_overrides_output() -> None:
    cfg = load_config(output="human", quiet=True)
    assert cfg.effective_output() == "quiet"


def test_output_passthrough() -> None:
    cfg = load_config(output="json")
    assert cfg.effective_output() == "json"


def test_load_config_uses_saved_token_when_env_token_is_absent(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    save_profile(token="saved-token", base_url="http://localhost:8000", config_path=path)
    cfg = load_config(config_path=path)
    assert cfg.token == "saved-token"


def test_load_config_uses_saved_base_url(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    save_profile(token="t", base_url="http://saved:9000", config_path=path)
    cfg = load_config(config_path=path)
    assert cfg.base_url == "http://saved:9000"


def test_environment_token_overrides_saved_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.toml"
    save_profile(token="saved-token", base_url="http://localhost:8000", config_path=path)
    monkeypatch.setenv("ATLAS_TOKEN", "env-token")
    assert load_config(config_path=path).token == "env-token"


def test_environment_base_url_overrides_saved_base_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.toml"
    save_profile(token="t", base_url="http://saved:9000", config_path=path)
    monkeypatch.setenv("ATLAS_BASE_URL", "http://env:7000")
    assert load_config(config_path=path).base_url == "http://env:7000"


def test_clear_saved_token_preserves_base_url(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    save_profile(token="saved-token", base_url="http://localhost:8000", config_path=path)
    clear_saved_token(config_path=path)
    cfg = load_config(config_path=path)
    assert cfg.token is None
    assert cfg.base_url == "http://localhost:8000"


def test_default_config_path_under_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_config_path() == tmp_path / "Atlas" / "config.toml"
