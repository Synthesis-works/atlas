"""Leaderboard DTOs — field-for-field mirror of ``apps/backend/schemas/leaderboard.py``."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from atlas_sdk.models.benchmarks import PageResponse


class LeaderboardType(StrEnum):
    """Scope of a leaderboard (mirrors domain ``LeaderboardType``)."""

    BENCHMARK = "BENCHMARK"
    CAPABILITY = "CAPABILITY"
    GLOBAL = "GLOBAL"
    ORGANIZATION = "ORGANIZATION"


class LeaderboardEntryRead(BaseModel):
    """Single row in a leaderboard.

    Mirrors ``apps/backend/schemas/leaderboard.py::LeaderboardEntryRead``.
    """

    rank: int
    model_name: str
    overall_score: float
    benchmark_count: int
    last_updated: datetime
    rank_delta: int | None = None
    metadata: dict[str, Any] | None = None


class LeaderboardRead(BaseModel):
    """Full paginated leaderboard response with context metadata.

    Returned directly by ``GET /api/v1/benchmarks/{version_id}/leaderboard``
    (not wrapped in ``APIResponse``), like the execution/report endpoints.
    """

    leaderboard_type: LeaderboardType
    title: str
    description: str | None = None
    benchmark_version_id: str | None = None
    capability_id: str | None = None
    entries: PageResponse[LeaderboardEntryRead]


class ModelSummary(BaseModel):
    """High-level aggregate overview of a model's performance.

    Mirrors ``apps/backend/schemas/leaderboard.py::ModelSummary``.
    Returned directly by ``GET /api/v1/models/{model_name}/summary``
    (not wrapped in ``APIResponse``).  An unknown model yields a 200
    with ``benchmarks == 0`` and null statistics, not a 404.
    """

    model: str
    benchmarks: int
    best_rank: int | None = None
    average_rank: float | None = None
    average_score: float | None = None
    last_execution: datetime | None = None
    latest_delta: int | None = None


class TrendPoint(BaseModel):
    """Single point in a model's performance history.

    Mirrors ``apps/backend/schemas/leaderboard.py::TrendPoint``.
    Returned as bare ``list[TrendPoint]`` by
    ``GET /api/v1/models/{model_name}/history``.  An unknown model
    yields a 200 with an empty list, not a 404.
    """

    timestamp: datetime
    score: float
    rank: int | None = None
    benchmark_version: str | None = None
    execution_id: str


class ModelBenchmarkVersionHistory(BaseModel):
    """History for one version of a benchmark for a single model.

    Mirrors ``apps/backend/schemas/leaderboard.py::ModelBenchmarkVersionHistory``.
    """

    version_string: str
    history: list[TrendPoint]


class ModelBenchmarkHistory(BaseModel):
    """A model's performance history grouped by benchmark.

    Mirrors ``apps/backend/schemas/leaderboard.py::ModelBenchmarkHistory``.
    Returned as bare ``list[ModelBenchmarkHistory]`` by
    ``GET /api/v1/models/{model_name}/benchmarks``.  An unknown model
    yields a 200 with an empty list, not a 404.
    """

    benchmark_name: str
    versions: list[ModelBenchmarkVersionHistory]
