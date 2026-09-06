"""Typed SDK error hierarchy.

Maps HTTP/API responses into typed exceptions that the CLI will later
translate into exit codes.  The SDK itself must NOT know about exit codes.
"""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """Base for all Atlas API errors.

    Attributes:
        status: HTTP status code (e.g. 401, 404, 500).
        code: Application-level error code string from the API (e.g. ``"VALIDATION_ERROR"``).
        message: Human-readable error message from the API.
        details: Arbitrary additional context from the API error payload.
    """

    def __init__(
        self,
        *,
        status: int,
        code: str = "",
        message: str = "",
        details: Any | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message or code or f"HTTP {status}")


class AuthError(ApiError):
    """401 Unauthorized — token missing, invalid, or expired."""


class ForbiddenError(ApiError):
    """403 Forbidden — authenticated but not authorized."""


class NotFoundError(ApiError):
    """404 Not Found."""


class ValidationError(ApiError):
    """422 Unprocessable Entity — request failed server-side validation."""


class ConflictError(ApiError):
    """409 Conflict — request conflicts with current state."""


class RateLimitedError(ApiError):
    """429 Too Many Requests."""


class ServerError(ApiError):
    """5xx — server-side failure."""


class NetworkError(Exception):
    """Connection failure, timeout, or DNS resolution error.

    Wraps ``httpx.TransportError`` subclasses.  Not a subclass of
    ``ApiError`` because no HTTP response was received.
    """

    def __init__(self, *, message: str = "", wrapped: BaseException | None = None) -> None:
        self.wrapped = wrapped
        super().__init__(message or str(wrapped))


# ── mapping helper ────────────────────────────────────────────────────

_STATUS_TO_ERROR: dict[int, type[ApiError]] = {
    401: AuthError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitedError,
}


def error_for_status(status: int, **kwargs: Any) -> ApiError:
    """Return the appropriate ``ApiError`` subclass for *status*.

    Falls back to ``ServerError`` for 5xx and ``ApiError`` for anything else.
    """
    cls = _STATUS_TO_ERROR.get(status)
    if cls is not None:
        return cls(status=status, **kwargs)
    if 500 <= status < 600:
        return ServerError(status=status, **kwargs)
    return ApiError(status=status, **kwargs)
