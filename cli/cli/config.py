"""Configuration — env vars + CLI flags + built-in defaults (§5.1).

Precedence (highest wins):
  CLI flags > environment variables > profile > built-in defaults.

For the skeleton, only env vars and defaults are implemented.
Profile file support (config.toml) is a Phase 1 addition.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_DEFAULT_BASE_URL = "http://localhost:8000"
_DEFAULT_TIMEOUT = 60.0
_DEFAULT_OUTPUT = "human"


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

    def effective_output(self) -> str:
        """Return the effective output mode, respecting --quiet shorthand."""
        if self.quiet:
            return "quiet"
        return self.output


def load_config(
    *,
    base_url: str | None = None,
    timeout: float | None = None,
    output: str | None = None,
    profile: str | None = None,
    no_color: bool = False,
    quiet: bool = False,
) -> AtlasConfig:
    """Build an AtlasConfig from flag values, env vars, and defaults.

    Precedence: CLI flags (if provided) > env vars > defaults.
    """
    resolved_base_url = (
        base_url
        or os.environ.get("ATLAS_BASE_URL")
        or _DEFAULT_BASE_URL
    )
    resolved_timeout = (
        timeout
        if timeout is not None
        else _env_float("ATLAS_TIMEOUT", _DEFAULT_TIMEOUT)
    )
    resolved_output = (
        output
        or os.environ.get("ATLAS_OUTPUT")
        or _DEFAULT_OUTPUT
    )
    resolved_profile = (
        profile
        or os.environ.get("ATLAS_PROFILE")
        or "default"
    )

    return AtlasConfig(
        base_url=resolved_base_url,
        timeout=resolved_timeout,
        output=resolved_output,
        profile=resolved_profile,
        no_color=no_color,
        quiet=quiet,
        token=os.environ.get("ATLAS_TOKEN"),
    )


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
