"""Tests for config precedence — CLI flags > env vars > defaults."""

from __future__ import annotations

from cli.config import load_config


def test_defaults() -> None:
    cfg = load_config()
    assert cfg.base_url == "http://localhost:8000"
    assert cfg.timeout == 60.0
    assert cfg.output == "human"
    assert cfg.profile == "default"
    assert cfg.no_color is False
    assert cfg.quiet is False


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


def test_quiet_overrides_output() -> None:
    cfg = load_config(output="human", quiet=True)
    assert cfg.effective_output() == "quiet"


def test_output_passthrough() -> None:
    cfg = load_config(output="json")
    assert cfg.effective_output() == "json"
