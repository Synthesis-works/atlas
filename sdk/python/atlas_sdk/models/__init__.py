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
from atlas_sdk.models.health import HealthData, LivenessResponse, ReadinessResponse
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
    "DashboardActivity",
    "DashboardCapability",
    "DashboardCapabilityScore",
    "DashboardHierarchy",
    "DashboardItem",
    "DashboardRuntime",
    "DashboardSnapshot",
    "DashboardSummary",
    "ArtifactResponse",
    "ExecutionAttemptResponse",
    "ExecutionCreateRequest",
    "ExecutionListResponse",
    "ExecutionPage",
    "ExecutionResponse",
    "ExecutionState",
    "ExecutionHistoryRead",
    "ModelActivityRead",
    "HealthData",
    "LivenessResponse",
    "ReadinessResponse",
    "LeaderboardEntryRead",
    "LeaderboardRead",
    "LeaderboardType",
    "ModelBenchmarkHistory",
    "ModelBenchmarkVersionHistory",
    "ModelRead",
    "ModelStatus",
    "ModelSummary",
    "TrendPoint",
    "PaginatedReportRunsRead",
    "ReportRunEntryRead",
    "ReportRunStatus",
    "CapabilityScoreRead",
    "ReportSummaryRead",
    "DownloadResult",
    "APIResponse",
    "APIErrorResponse",
    "ErrorDetail",
    "ResponseMeta",
]
