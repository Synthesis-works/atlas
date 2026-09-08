"""Dashboard DTOs — mirror ``apps/backend/routers/dashboard.py::get_dashboard``.

The endpoint returns a bare dict (no ``APIResponse`` envelope).  Structural
sections are typed; free-form job/activity streams are kept as generic dict
lists so additions in the backend do not break the SDK.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardItem(BaseModel):
    """A single execution row in ``running_jobs`` / ``active_executions``."""

    id: str
    model: str
    benchmark: str
    status: str
    progress: int
    is_verified: bool = False
    source: str = "real"


class DashboardActivity(BaseModel):
    """A single timeline entry in the dashboard ``activity`` stream."""

    id: str
    type: str
    title: str
    description: str
    timestamp: str | None = None


class DashboardSummary(BaseModel):
    """Run counters by status."""

    active_runs_count: int
    queued_runs_count: int
    completed_runs_count: int
    failed_runs_count: int
    cancelled_runs_count: int
    total_runs_count: int


class DashboardHierarchy(BaseModel):
    """Resource counts across the platform."""

    models: int
    benchmarks: int
    datasets: int
    evaluations: int
    reports: int


class DashboardRuntime(BaseModel):
    """Engine runtime metrics."""

    engine_status: str
    total_benchmarks: int
    total_evaluations: int
    total_models: int
    avg_runtime_sec: float


class DashboardCapabilityScore(BaseModel):
    """Per-domain average score for the current top model."""

    domain: str
    score: float


class DashboardCapability(BaseModel):
    """Summary for the current #1 leaderboard model (may be absent)."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    provider: str
    rank: int
    score: float
    capabilities: list[DashboardCapabilityScore] = []


class DashboardSnapshot(BaseModel):
    """Aggregated workspace dashboard.

    Returned directly by ``GET /api/v1/dashboard`` (not wrapped in
    ``APIResponse``).
    """

    generated_at: datetime
    version: str
    summary: DashboardSummary
    hierarchy: DashboardHierarchy
    running_jobs: list[DashboardItem]
    recent_verified_runs: list[DashboardItem]
    active_executions: list[DashboardItem]
    activity: list[DashboardActivity]
    runtime: DashboardRuntime
    capability: DashboardCapability | None = None
