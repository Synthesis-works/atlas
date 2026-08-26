"""Pydantic DTOs that mirror Atlas ``/api/v1`` response schemas.

Field-for-field correspondence with the backend — no renaming, no
"prettier" fields.  The JSON contract depends on this.
"""

from atlas_sdk.models.auth import AuthUserRead, TokenResponse
from atlas_sdk.models.benchmarks import (
    BenchmarkRead,
    BenchmarkVersionRead,
    PageResponse,
)
from atlas_sdk.models.executions import (
    ArtifactResponse,
    ExecutionAttemptResponse,
    ExecutionCreateRequest,
    ExecutionListResponse,
    ExecutionPage,
    ExecutionResponse,
    ExecutionState,
)
from atlas_sdk.models.health import HealthData, LivenessResponse, ReadinessResponse
from atlas_sdk.models.responses import (
    APIErrorResponse,
    APIResponse,
    ErrorDetail,
    ResponseMeta,
)

__all__ = [
    "AuthUserRead",
    "TokenResponse",
    "BenchmarkRead",
    "BenchmarkVersionRead",
    "PageResponse",
    "ArtifactResponse",
    "ExecutionAttemptResponse",
    "ExecutionCreateRequest",
    "ExecutionListResponse",
    "ExecutionPage",
    "ExecutionResponse",
    "ExecutionState",
    "HealthData",
    "LivenessResponse",
    "ReadinessResponse",
    "APIResponse",
    "APIErrorResponse",
    "ErrorDetail",
    "ResponseMeta",
]
