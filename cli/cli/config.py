"""Configuration — env vars + CLI flags + saved profile + built-in defaults (§5.1).

Precedence (highest wins):
  CLI flags > environment variables > saved profile > built-in defaults.

Credentials are persisted per-user (never in the repository) under
``%APPDATA%\\Atlas\\config.toml`` (``default_config_path()``).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_BASE_URL = "http://localhost:8000"
_DEFAULT_TIMEOUT = 60.0
_DEFAULT_OUTPUT = "human"
_DEFAULT_RETRIES = 3  # mirrors the SDK's built-in retry cap; 0 disables retries


@dataclass
class AtlasConfig:
    """Resolved CLI configuration for a single invocation."""

    base_url: str = _DEFAULT_BASE_URL
    timeout: float = _DEFAULT_TIMEOUT
    output: str = _DEFAULT_OUTPUT
    profile: str = "default"
    no_color: bool = False
    quiet: bool = False
    token: str | None = None
    retries: int = _DEFAULT_RETRIES

    def effective_output(self) -> str:
        """Return the effective output mode, respecting --quiet shorthand."""
        if self.quiet:
            return "quiet"
        return self.output


def default_config_path() -> Path:
    """Per-user profile file path (never inside the repository)."""
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "Atlas" / "config.toml"


def load_config(
    *,
    base_url: str | None = None,
    timeout: float | None = None,
    output: str | None = None,
    profile: str | None = None,
    no_color: bool = False,
    quiet: bool = False,
    retries: int | None = None,
    config_path: Path | None = None,
) -> AtlasConfig:
    """Build an AtlasConfig from flag values, env vars, profile, and defaults.

    Precedence: CLI flags (if provided) > env vars > saved profile > defaults.
    """
    resolved_profile = profile or os.environ.get("ATLAS_PROFILE") or "default"
    saved = _read_profiles(config_path).get(resolved_profile, {})

    resolved_base_url = (
        base_url or os.environ.get("ATLAS_BASE_URL") or saved.get("base_url") or _DEFAULT_BASE_URL
    )
    resolved_timeout = (
        timeout if timeout is not None else _env_float("ATLAS_TIMEOUT", _DEFAULT_TIMEOUT)
    )
    resolved_output = output or os.environ.get("ATLAS_OUTPUT") or _DEFAULT_OUTPUT
    resolved_retries = (
        retries if retries is not None else _env_int("ATLAS_RETRIES", _DEFAULT_RETRIES)
    )

    return AtlasConfig(
        base_url=resolved_base_url,
        timeout=resolved_timeout,
        output=resolved_output,
        profile=resolved_profile,
        no_color=no_color,
        quiet=quiet,
        token=os.environ.get("ATLAS_TOKEN") or saved.get("token"),
        retries=resolved_retries,
    )


def save_profile(
    *,
    token: str,
    base_url: str,
    profile: str = "default",
    config_path: Path | None = None,
) -> None:
    """Persist the access token and base URL for a profile (UTF-8 TOML)."""
    profiles = _read_profiles(config_path)
    profiles[profile] = {"base_url": base_url, "token": token}
    _write_profiles(profiles, config_path)


def clear_saved_token(
    *,
    profile: str = "default",
    config_path: Path | None = None,
) -> None:
    """Remove the saved token for a profile, preserving other settings."""
    profiles = _read_profiles(config_path)
    if profile in profiles:
        profiles[profile].pop("token", None)
    _write_profiles(profiles, config_path)


def _read_profiles(config_path: Path | None = None) -> dict[str, dict[str, str]]:
    path = config_path or default_config_path()
    if not path.exists():
        return {}
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        # A corrupt or unreadable profile file must never break the CLI.
        return {}
    profiles: dict[str, dict[str, str]] = {}
    for name, value in raw.items():
        if isinstance(value, dict):
            profiles[name] = {k: v for k, v in value.items() if isinstance(v, str)}
    return profiles


def _write_profiles(
    profiles: dict[str, dict[str, str]],
    config_path: Path | None = None,
) -> None:
    path = config_path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for name in sorted(profiles):
        lines.append(f"[{name}]")
        for key, value in profiles[name].items():
            lines.append(f"{key} = {_toml_quote(value)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
