import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from apps.backend.dependencies import get_leaderboard_app_service, require_authenticated
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.leaderboard import LeaderboardRead
from apps.backend.services.leaderboard import LeaderboardApplicationService

router = APIRouter(tags=["Leaderboard"])


@router.get(
    "/benchmarks/{benchmark_version_id}/leaderboard",
    response_model=LeaderboardRead,
    summary="Get Benchmark Leaderboard",
)
def get_benchmark_leaderboard(
    benchmark_version_id: uuid.UUID,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    claims: TokenClaims = Depends(require_authenticated),
    service: LeaderboardApplicationService = Depends(get_leaderboard_app_service),
) -> LeaderboardRead:
    """
    Retrieves the leaderboard for a specific benchmark version, ranking models based on their overall score.
    """
    # Lightweight cache header, per PR21 spec
    response.headers["Cache-Control"] = "max-age=60"

    return service.get_benchmark_leaderboard(
        benchmark_version_id=benchmark_version_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/capabilities/{capability_id}/leaderboard",
    response_model=LeaderboardRead,
    summary="Get Capability Leaderboard",
)
def get_capability_leaderboard(
    capability_id: uuid.UUID,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    claims: TokenClaims = Depends(require_authenticated),
    service: LeaderboardApplicationService = Depends(get_leaderboard_app_service),
) -> LeaderboardRead:
    """
    Retrieves the global leaderboard for a specific capability, aggregating scores across all its underlying benchmarks.
    """
    response.headers["Cache-Control"] = "max-age=60"

    return service.get_capability_leaderboard(
        capability_id=capability_id,
        limit=limit,
        offset=offset,
    )
