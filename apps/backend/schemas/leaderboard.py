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


class TrendPoint(BaseModel):
    """
    Represents a single point in time for a model's performance on a specific target.
    """

    timestamp: datetime = Field(..., description="The time of the snapshot or execution")
    score: float = Field(..., description="The overall score at this point in time")
    rank: int | None = Field(
        None, description="The model's rank at this point in time, if available"
    )
    benchmark_version: str | None = Field(
        None, description="The version of the benchmark, if applicable"
    )
    execution_id: str = Field(..., description="The execution that produced this score")


class ModelSummary(BaseModel):
    """
    High-level aggregate overview of a model's performance across the platform.
    """

    model: str = Field(..., description="The model's identifier")
    benchmarks: int = Field(..., description="Total number of distinct benchmarks evaluated")
    best_rank: int | None = Field(None, description="The best rank achieved on any leaderboard")
    average_rank: float | None = Field(
        None, description="Average rank across all evaluated leaderboards"
    )
    average_score: float | None = Field(
        None, description="Average score across all evaluated leaderboards"
    )
    last_execution: datetime | None = Field(
        None, description="Timestamp of the most recent execution"
    )
    latest_delta: int | None = Field(None, description="Change in average rank since last snapshot")


class ModelBenchmarkVersionHistory(BaseModel):
    """
    History for a specific version of a benchmark.
    """

    version_string: str = Field(..., description="The version string (e.g. 'v1', 'v2')")
    history: list[TrendPoint] = Field(
        ..., description="Chronological trend points for this version"
    )


class ModelBenchmarkHistory(BaseModel):
    """
    Groups a model's performance history under a conceptual Benchmark,
    allowing continuous timelines across version changes.
    """

    benchmark_name: str = Field(..., description="The canonical name of the benchmark")
    versions: list[ModelBenchmarkVersionHistory] = Field(
        ..., description="History grouped by version"
    )
