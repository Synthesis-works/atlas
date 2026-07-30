from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from apps.backend.schemas.query import PageResponse


class LeaderboardType(str, Enum):
    BENCHMARK = "BENCHMARK"
    CAPABILITY = "CAPABILITY"
    GLOBAL = "GLOBAL"
    ORGANIZATION = "ORGANIZATION"


class LeaderboardEntryRead(BaseModel):
    """
    Represents a single row in a leaderboard.
    """

    rank: int = Field(..., description="The calculated rank of the model on this leaderboard")
    model_name: str = Field(..., description="The canonical identifier of the evaluated model")
    overall_score: float = Field(
        ..., description="The overall score determined by the reporting engine"
    )
    benchmark_count: int = Field(
        ..., description="The number of underlying benchmarks aggregated for this score"
    )
    last_updated: datetime = Field(
        ...,
        description="The timestamp of the latest successful execution contributing to this score",
    )
    rank_delta: int | None = Field(
        None, description="The change in rank compared to the previous snapshot (e.g., +2, -1, 0)"
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Additional context or secondary scores (e.g., capability_score)"
    )


class LeaderboardRead(BaseModel):
    """
    Represents a full paginated leaderboard response with context metadata.
    """

    leaderboard_type: LeaderboardType = Field(..., description="The scope of the leaderboard")
    title: str = Field(
        ..., description="Display title (e.g., 'HumanEval v2' or 'Reasoning Capability')"
    )
    description: str | None = Field(
        None, description="Optional description of the leaderboard's focus"
    )
    benchmark_version_id: str | None = Field(
        None, description="If scoped to a specific benchmark version"
    )
    capability_id: str | None = Field(None, description="If scoped to a specific capability")
    entries: PageResponse[LeaderboardEntryRead] = Field(
        ..., description="Paginated entries of the leaderboard"
    )


class LeaderboardFilterRequest(BaseModel):
    """
    Standard filters applied when retrieving leaderboards.
    """

    capability_id: str | None = Field(None, description="Filter for capability leaderboards")
    benchmark_id: str | None = Field(
        None, description="Filter for benchmark leaderboards (groups versions)"
    )
    organization_id: str | None = Field(
        None, description="Filter for organization-scoped leaderboards"
    )
