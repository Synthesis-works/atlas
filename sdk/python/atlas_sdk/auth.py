"""Token supply strategies for SDK authentication.

The SDK owns *attaching* credentials to HTTP requests.
The CLI owns credential *storage and configuration*.

A ``TokenSupplier`` is a zero-argument callable that returns a bearer token
string.  The ``AtlasClient`` calls it before every request.
"""

from __future__ import annotations

from typing import Protocol


class TokenSupplier(Protocol):
    """Protocol for token supply — any callable ``() -> str``."""

    def __call__(self) -> str: ...  # pragma: no cover


class StaticTokenSupplier:
    """Returns a fixed token.  Useful for testing and CI environments."""

    def __init__(self, token: str) -> None:
        self._token = token

    def __call__(self) -> str:
        return self._token
