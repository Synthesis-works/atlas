"""Tests for exit-code mapping (§10)."""

from __future__ import annotations

import pytest
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

from cli.errors import ExitCode, exit_code_for_error


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (AuthError(status=401), ExitCode.AUTH_REQUIRED),
        (ForbiddenError(status=403), ExitCode.FORBIDDEN),
        (NotFoundError(status=404), ExitCode.NOT_FOUND),
        (ValidationError(status=422), ExitCode.VALIDATION),
        (ConflictError(status=409), ExitCode.CONFLICT),
        (RateLimitedError(status=429), ExitCode.NETWORK),
        (ServerError(status=500), ExitCode.UNSPECIFIED),
        (ServerError(status=502), ExitCode.UNSPECIFIED),
        (NetworkError(message="timeout"), ExitCode.NETWORK),
        (ApiError(status=418), ExitCode.UNSPECIFIED),
        (RuntimeError("unexpected"), ExitCode.UNSPECIFIED),
        (KeyboardInterrupt(), ExitCode.INTERRUPTED),
    ],
    ids=[
        "401->3",
        "403->4",
        "404->5",
        "422->7",
        "409->8",
        "429->6",
        "500->1",
        "502->1",
        "network->6",
        "unknown_api->1",
        "runtime->1",
        "keyboard->130",
    ],
)
def test_exit_code_mapping(exc: Exception, expected: int) -> None:
    assert exit_code_for_error(exc) == expected


def test_exit_code_constants() -> None:
    assert ExitCode.SUCCESS == 0
    assert ExitCode.UNSPECIFIED == 1
    assert ExitCode.USAGE == 2
    assert ExitCode.AUTH_REQUIRED == 3
    assert ExitCode.FORBIDDEN == 4
    assert ExitCode.NOT_FOUND == 5
    assert ExitCode.NETWORK == 6
    assert ExitCode.VALIDATION == 7
    assert ExitCode.CONFLICT == 8
    assert ExitCode.INTERRUPTED == 130
