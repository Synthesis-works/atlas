import uuid
from ..core.cache import ReportCache
from ..models.read_models import (
    CapabilityDashboardRead,
    HistoryEntryRead,
    LeaderboardRead,
    PaginatedReportRunsRead,
    ReportRunsFilter,
    ReportSummaryRead,
)
from ..services.queries import (
    CapabilityQueryService,
    HistoryQueryService,
    LeaderboardQueryService,
    RunQueryService,
)
from ..strategies.leaderboard import (
    CapabilityLeaderboardStrategy,
    OverallLeaderboardStrategy,
)


class ReportingService:
    """
    The central business logic layer for reporting.
    Coordinates Query Services, Caching, and Strategies.
    """

    def __init__(
        self,
        cache: ReportCache,
        capability_query: CapabilityQueryService,
        leaderboard_query: LeaderboardQueryService,
        history_query: HistoryQueryService,
        run_query: RunQueryService | None = None,
    ):
        self.cache = cache
        self.capability_query = capability_query
        self.leaderboard_query = leaderboard_query
        self.history_query = history_query
        if run_query is None:
            # Fallback if not injected explicitly in old callers
            from ..repositories.reporting_repo import ReportingRepository

            self.run_query = RunQueryService(ReportingRepository(capability_query.repo.db))
        else:
            self.run_query = run_query

        self.leaderboard_strategies = {
            "overall": OverallLeaderboardStrategy(),
            "capability": CapabilityLeaderboardStrategy(),
        }

    def get_run_summary(self, run_id: uuid.UUID) -> ReportSummaryRead | None:
        cache_key = f"run_summary:{run_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached  # type: ignore

        data = self.run_query.get_run_summary(run_id)
        if data and data.evaluation_status in ("COMPLETED", "FAILED", "CANCELLED"):
            self.cache.set(cache_key, data)
        return data

    def get_runs_filtered(self, filter_obj: ReportRunsFilter) -> PaginatedReportRunsRead:
        return self.run_query.get_runs_filtered(filter_obj)

    def get_capability_dashboard(self, model_identifier: str) -> CapabilityDashboardRead | None:
        cache_key = f"capability_dashboard:{model_identifier}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached  # type: ignore

        data = self.capability_query.get_capability_dashboard(model_identifier)
        if data:
            self.cache.set(cache_key, data)
        return data

    def get_leaderboard(self, strategy_name: str, limit: int = 10) -> LeaderboardRead:
        cache_key = f"leaderboard:{strategy_name}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached  # type: ignore

        strategy = self.leaderboard_strategies.get(strategy_name, OverallLeaderboardStrategy())
        data = strategy.execute(self.leaderboard_query, limit=limit)

        self.cache.set(cache_key, data)
        return data

    def get_history(self, limit: int = 50, offset: int = 0) -> tuple[list[HistoryEntryRead], int]:
        return self.history_query.get_paginated_history(limit, offset)
