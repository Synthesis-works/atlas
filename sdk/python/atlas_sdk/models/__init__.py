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
from atlas_sdk.models.datasets import DatasetRead, DatasetValidationResult, DatasetVersionRead
from atlas_sdk.models.evaluation import (
    EvaluationCaseItem,
    EvaluationCaseWriteResponse,
    EvaluationCaseWritten,
    EvaluationEnqueuedRead,
    EvaluationResultItemRead,
    EvaluationResultsRead,
    ExecutionCompareItemRead,
    ExecutionCompareResponse,
    ReportListRead,
    ReportMetricRead,
    ReportRead,
    ReportVersionRead,
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
from atlas_sdk.models.projects import OrganizationRead, ProjectRead
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
from atlas_sdk.models.search import SearchResult

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
    "DatasetRead",
    "DatasetValidationResult",
    "DatasetVersionRead",
    "ArtifactResponse",
    "ExecutionAttemptResponse",
    "ExecutionCreateRequest",
    "ExecutionListResponse",
    "ExecutionPage",
    "ExecutionResponse",
    "ExecutionState",
    "EvaluationCaseItem",
    "EvaluationCaseWriteResponse",
    "EvaluationCaseWritten",
    "EvaluationEnqueuedRead",
    "EvaluationResultItemRead",
    "EvaluationResultsRead",
    "ExecutionCompareItemRead",
    "ExecutionCompareResponse",
    "ReportListRead",
    "ReportMetricRead",
    "ReportRead",
    "ReportVersionRead",
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
    "OrganizationRead",
    "ProjectRead",
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
    "SearchResult",
]
