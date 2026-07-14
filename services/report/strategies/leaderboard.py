import abc
from ..services.queries import LeaderboardQueryService
from ..models.read_models import LeaderboardRead

class LeaderboardStrategy(abc.ABC):
    @abc.abstractmethod
    def execute(self, query_service: LeaderboardQueryService, **kwargs) -> LeaderboardRead:
        pass

class OverallLeaderboardStrategy(LeaderboardStrategy):
    def execute(self, query_service: LeaderboardQueryService, **kwargs) -> LeaderboardRead:
        limit = kwargs.get('limit', 10)
        return query_service.get_overall_leaderboard(limit=limit)

class CapabilityLeaderboardStrategy(LeaderboardStrategy):
    def execute(self, query_service: LeaderboardQueryService, **kwargs) -> LeaderboardRead:
        # Placeholder for capability-specific leaderboard
        # e.g., querying for a specific capability ID
        # return query_service.get_capability_leaderboard(...)
        return LeaderboardRead(strategy="capability", entries=[])
