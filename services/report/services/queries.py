from typing import List, Optional
from uuid import UUID

from ..models.read_models import (
    CapabilityDashboardRead, 
    CapabilityScoreRead,
    LeaderboardRead,
    LeaderboardEntryRead,
    HistoryEntryRead
)
from ..repositories.reporting_repo import ReportingRepository

class CapabilityQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def get_capability_dashboard(self, model_identifier: str) -> Optional[CapabilityDashboardRead]:
        profile = self.repo.get_latest_capability_profile(model_identifier)
        if not profile:
            return None
        
        # In a real scenario, CapabilityScore joins with Capability to get the name
        # We mock the capability_name if the capability relation is not fully fetched.
        scores = []
        for score_model in profile.scores:
            scores.append(CapabilityScoreRead(
                capability_name=f"cap_{score_model.capability_id}", # Placeholder for demonstration
                score=score_model.score
            ))
            
        return CapabilityDashboardRead(
            model_identifier=model_identifier,
            overall_score=profile.overall_score or 0.0,
            scores=scores
        )

class LeaderboardQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def get_overall_leaderboard(self, limit: int = 10) -> LeaderboardRead:
        data = self.repo.get_overall_leaderboard_data(limit=limit)
        entries = []
        for rank, (model, score) in enumerate(data, start=1):
            entries.append(LeaderboardEntryRead(
                rank=rank,
                model_identifier=model,
                score=score or 0.0
            ))
        return LeaderboardRead(
            strategy="overall",
            entries=entries
        )

class HistoryQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def get_paginated_history(self, limit: int = 50, offset: int = 0) -> tuple[List[HistoryEntryRead], int]:
        runs, total = self.repo.get_history(limit, offset)
        
        items = []
        for run in runs:
            # We'd typically also fetch evaluation results to know if it passed, but keep it simple for read model
            items.append(HistoryEntryRead(
                run_id=run.id,
                target_model=run.target_model,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                passed=None # Would compute from evaluations
            ))
        return items, total

class TrendQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    # Add trend querying logic here later (e.g. daily average scores)
    pass
