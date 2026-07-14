from typing import Optional, List
from ..core.cache import ReportCache
from ..services.queries import CapabilityQueryService, LeaderboardQueryService, HistoryQueryService
from ..models.read_models import CapabilityDashboardRead, LeaderboardRead, HistoryEntryRead
from ..strategies.leaderboard import LeaderboardStrategy, OverallLeaderboardStrategy, CapabilityLeaderboardStrategy

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
        history_query: HistoryQueryService
    ):
        self.cache = cache
        self.capability_query = capability_query
        self.leaderboard_query = leaderboard_query
        self.history_query = history_query

        self.leaderboard_strategies = {
            "overall": OverallLeaderboardStrategy(),
            "capability": CapabilityLeaderboardStrategy(),
        }

    def get_capability_dashboard(self, model_identifier: str) -> Optional[CapabilityDashboardRead]:
        cache_key = f"capability_dashboard:{model_identifier}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        data = self.capability_query.get_capability_dashboard(model_identifier)
        if data:
            self.cache.set(cache_key, data)
        return data

    def get_leaderboard(self, strategy_name: str, limit: int = 10) -> LeaderboardRead:
        cache_key = f"leaderboard:{strategy_name}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        strategy = self.leaderboard_strategies.get(strategy_name, OverallLeaderboardStrategy())
        data = strategy.execute(self.leaderboard_query, limit=limit)
        
        self.cache.set(cache_key, data)
        return data
        
    def get_history(self, limit: int = 50, offset: int = 0) -> tuple[List[HistoryEntryRead], int]:
        return self.history_query.get_paginated_history(limit, offset)
