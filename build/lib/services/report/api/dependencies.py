from atlas_db.core.session import get_db
from fastapi import Depends
from sqlalchemy.orm import Session

from ..core.cache import NoopReportCache, ReportCache
from ..repositories.reporting_repo import ReportingRepository
from ..services.queries import (
    CapabilityQueryService,
    HistoryQueryService,
    LeaderboardQueryService,
    RunQueryService,
)
from ..services.reporting import ReportingService


def get_report_cache() -> ReportCache:
    return NoopReportCache()


def get_reporting_repository(db: Session = Depends(get_db)) -> ReportingRepository:
    return ReportingRepository(db)


def get_capability_query_service(
    repo: ReportingRepository = Depends(get_reporting_repository),
) -> CapabilityQueryService:
    return CapabilityQueryService(repo)


def get_leaderboard_query_service(
    repo: ReportingRepository = Depends(get_reporting_repository),
) -> LeaderboardQueryService:
    return LeaderboardQueryService(repo)


def get_history_query_service(
    repo: ReportingRepository = Depends(get_reporting_repository),
) -> HistoryQueryService:
    return HistoryQueryService(repo)


def get_run_query_service(
    repo: ReportingRepository = Depends(get_reporting_repository),
) -> RunQueryService:
    return RunQueryService(repo)


def get_reporting_service(
    cache: ReportCache = Depends(get_report_cache),
    capability_query: CapabilityQueryService = Depends(get_capability_query_service),
    leaderboard_query: LeaderboardQueryService = Depends(get_leaderboard_query_service),
    history_query: HistoryQueryService = Depends(get_history_query_service),
    run_query: RunQueryService = Depends(get_run_query_service),
) -> ReportingService:
    return ReportingService(
        cache=cache,
        capability_query=capability_query,
        leaderboard_query=leaderboard_query,
        history_query=history_query,
        run_query=run_query,
    )
