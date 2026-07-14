from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

#
# API DTOs
# The exact schemas returned over HTTP to the client.
#

class CapabilityScoreDTO(BaseModel):
    capability_name: str
    score: float
    
    model_config = ConfigDict(from_attributes=True)

class CapabilityDashboardDTO(BaseModel):
    model_identifier: str
    overall_score: float
    scores: List[CapabilityScoreDTO]
    
    model_config = ConfigDict(from_attributes=True)

class LeaderboardEntryDTO(BaseModel):
    rank: int
    model_identifier: str
    score: float
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(from_attributes=True)

class LeaderboardResponseDTO(BaseModel):
    strategy: str
    entries: List[LeaderboardEntryDTO]
    
    model_config = ConfigDict(from_attributes=True)

class TrendPointDTO(BaseModel):
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(from_attributes=True)

class TrendAnalysisResponseDTO(BaseModel):
    metric_name: str
    points: List[TrendPointDTO]
    moving_average: Optional[List[TrendPointDTO]] = None
    
    model_config = ConfigDict(from_attributes=True)

class BenchmarkPerformanceDTO(BaseModel):
    benchmark_id: UUID
    benchmark_name: str
    average_score: float
    total_runs: int
    
    model_config = ConfigDict(from_attributes=True)

from packages.core.models.pagination import PaginatedResponseDTO
from packages.core.models.health import SystemHealthDTO, VersionInfoDTO

class HistoryEntryDTO(BaseModel):
    run_id: UUID
    target_model: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    passed: Optional[bool]
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedHistoryResponseDTO(PaginatedResponseDTO[HistoryEntryDTO]):
    pass
