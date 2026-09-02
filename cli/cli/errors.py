"""Exit-code mapping — single source of truth per §10.

The SDK raises typed exceptions; this module maps them to process exit codes.
The CLI owns this mapping; the SDK must never know about exit codes.
"""

from __future__ import annotations

from atlas_sdk.errors import (
    ApiError,
    AuthError,
    ConflictError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    RateLimitedError,
    ServerError,
    ValidationError,
)


class ExitCode:
    """Integer constants for process exit codes (§10)."""

    SUCCESS = 0
    UNSPECIFIED = 1
    USAGE = 2
    AUTH_REQUIRED = 3
    FORBIDDEN = 4
    NOT_FOUND = 5
    NETWORK = 6
    VALIDATION = 7
    CONFLICT = 8
    WATCH_TIMEOUT = 9
    AGENT_UNAVAILABLE = 10  # agent brain (LLM) unavailable — see exit 10 usage
    INTERRUPTED = 130


def exit_code_for_error(exc: Exception) -> int:
    """Map an SDK exception (or KeyboardInterrupt) to a process exit code."""
    if isinstance(exc, KeyboardInterrupt):
        return ExitCode.INTERRUPTED
    if isinstance(exc, AuthError):
        return ExitCode.AUTH_REQUIRED
    if isinstance(exc, ForbiddenError):
        return ExitCode.FORBIDDEN
    if isinstance(exc, NotFoundError):
        return ExitCode.NOT_FOUND
    if isinstance(exc, ValidationError):
        return ExitCode.VALIDATION
    if isinstance(exc, ConflictError):
        return ExitCode.CONFLICT
    if isinstance(exc, RateLimitedError):
        return ExitCode.NETWORK
    if isinstance(exc, NetworkError):
        return ExitCode.NETWORK
    if isinstance(exc, ServerError):
        return ExitCode.UNSPECIFIED
    if isinstance(exc, ApiError):
        return ExitCode.UNSPECIFIED
    return ExitCode.UNSPECIFIED



