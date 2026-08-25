"""atlas-sdk: Python SDK for the Atlas control-plane API.

A thin HTTP client containing zero Atlas business logic.
CLI → atlas-sdk → HTTP → /api/v1.
"""

from atlas_sdk.auth import StaticTokenSupplier, TokenSupplier
from atlas_sdk.client import AtlasClient
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

__all__ = [
    "AtlasClient",
    "ApiError",
    "AuthError",
    "ConflictError",
    "ForbiddenError",
    "NetworkError",
    "NotFoundError",
    "RateLimitedError",
    "ServerError",
    "StaticTokenSupplier",
    "TokenSupplier",
    "ValidationError",
]

__version__ = "0.1.0"
