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
from atlas_sdk.models.benchmarks import (
    BenchmarkRead,
    BenchmarkVersionRead,
    PageResponse,
)
from atlas_sdk.models.dashboard import (
    DashboardActivity,
    DashboardCapability,
    DashboardCapabilityScore,
    DashboardHierarchy,
    DashboardItem,
    DashboardRuntime,
    DashboardSnapshot,
    DashboardSummary,
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
from atlas_sdk.models.history import ExecutionHistoryRead, ModelActivityRead
from atlas_sdk.models.leaderboard import (
    LeaderboardEntryRead,
    LeaderboardRead,
    LeaderboardType,
    ModelBenchmarkHistory,
    ModelBenchmarkVersionHistory,
    ModelSummary,
    TrendPoint,
)
from atlas_sdk.models.models import ModelRead, ModelStatus
from atlas_sdk.models.reports import (
    CapabilityScoreRead,
    DownloadResult,
    PaginatedReportRunsRead,
    ReportRunEntryRead,
    ReportRunStatus,
    ReportSummaryRead,
)

__all__ = [
    "AtlasClient",
    "ApiError",
    "AuthError",
    "ArtifactResponse",
    "BenchmarkRead",
    "BenchmarkVersionRead",
    "ConflictError",
    "DashboardActivity",
    "DashboardCapability",
    "DashboardCapabilityScore",
    "DashboardHierarchy",
    "DashboardItem",
    "DashboardRuntime",
    "DashboardSnapshot",
    "DashboardSummary",
    "ExecutionAttemptResponse",
    "ExecutionCreateRequest",
    "ExecutionHistoryRead",
    "ExecutionListResponse",
    "ExecutionPage",
    "ExecutionResponse",
    "ExecutionState",
    "ForbiddenError",
    "LeaderboardEntryRead",
    "LeaderboardRead",
    "LeaderboardType",
    "ModelActivityRead",
    "ModelBenchmarkHistory",
    "ModelBenchmarkVersionHistory",
    "ModelRead",
    "ModelStatus",
    "ModelSummary",
    "TrendPoint",
    "NetworkError",
    "NotFoundError",
    "PaginatedReportRunsRead",
    "PageResponse",
    "RateLimitedError",
    "ReportRunEntryRead",
    "ReportRunStatus",
    "CapabilityScoreRead",
    "ReportSummaryRead",
    "DownloadResult",
    "ServerError",
    "StaticTokenSupplier",
    "TokenSupplier",
    "ValidationError",
]

__version__ = "0.1.0"
