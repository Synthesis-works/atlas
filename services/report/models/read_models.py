import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

#
# Read Models
# Internal representations of aggregated data from the DB.
#


class ReportRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CapabilityScoreRead(BaseModel):
    capability_name: str
    score: float


class CapabilityDashboardRead(BaseModel):
    model_identifier: str
    overall_score: float
    scores: list[CapabilityScoreRead] = Field(default_factory=list)


class ReportSummaryRead(BaseModel):
    run_id: UUID
    benchmark_id: UUID
    benchmark_name: str
    benchmark_version: str
    target_model: str
    evaluation_status: ReportRunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    overall_score: float | None = None
    scores: list[CapabilityScoreRead] = Field(default_factory=list)


class ReportRunEntryRead(BaseModel):
    run_id: UUID
    benchmark_id: UUID
    benchmark_version: str
    target_model: str
    evaluation_status: ReportRunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    overall_score: float | None = None


class PaginatedReportRunsRead(BaseModel):
    items: list[ReportRunEntryRead]
    total: int
    page: int
    size: int


class ReportRunsFilter(BaseModel):
    status: ReportRunStatus | None = None
    benchmark_id: UUID | None = None
    benchmark_version: str | None = None
    target_model: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class LeaderboardEntryRead(BaseModel):
    rank: int
    model_identifier: str
    score: float
    metadata: dict[str, Any] = {}


class LeaderboardRead(BaseModel):
    strategy: str
    entries: list[LeaderboardEntryRead]


class TrendPointRead(BaseModel):
    timestamp: datetime
    value: float
    metadata: dict[str, Any] = {}


class TrendAnalysisRead(BaseModel):
    metric_name: str
    points: list[TrendPointRead]
    moving_average: list[TrendPointRead] | None = None


class BenchmarkPerformanceRead(BaseModel):
    benchmark_id: UUID
    benchmark_name: str
    average_score: float
    total_runs: int


class HistoryEntryRead(BaseModel):
    run_id: UUID
    target_model: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    passed: bool | None = None


class RunExportRowRead(BaseModel):
    run_id: UUID
    benchmark_id: UUID
    benchmark_version: str
    model_identifier: str
    execution_status: str
    evaluation_status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    test_case_id: UUID | None = None
    category: str | None = None
    difficulty: str | None = None
    prompt: dict | list | str | None = None
    expected_output: dict | list | str | None = None
    raw_output: dict | list | str | None = None
    tokens_used: int | None = None
    latency_ms: float | None = None
    passed: bool = False
    confidence: float | None = None
    failure_reasons: list[str] | None = None
