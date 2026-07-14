from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

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
    scores: List[CapabilityScoreRead]

class LeaderboardEntryRead(BaseModel):
    rank: int
    model_identifier: str
    score: float
    metadata: Dict[str, Any] = {}

class LeaderboardRead(BaseModel):
    strategy: str
    entries: List[LeaderboardEntryRead]

class TrendPointRead(BaseModel):
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = {}

class TrendAnalysisRead(BaseModel):
    metric_name: str
    points: List[TrendPointRead]
    moving_average: Optional[List[TrendPointRead]] = None

class BenchmarkPerformanceRead(BaseModel):
    benchmark_id: UUID
    benchmark_name: str
    average_score: float
    total_runs: int

class HistoryEntryRead(BaseModel):
    run_id: UUID
    target_model: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    passed: Optional[bool]
