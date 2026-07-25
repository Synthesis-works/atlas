from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

#
# Read Models
# Internal representations of aggregated data from the DB.
#


class CapabilityScoreRead(BaseModel):
    capability_name: str
    score: float


class CapabilityDashboardRead(BaseModel):
    model_identifier: str
    overall_score: float
    scores: list[CapabilityScoreRead]


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
    started_at: datetime | None
    completed_at: datetime | None
    passed: bool | None
