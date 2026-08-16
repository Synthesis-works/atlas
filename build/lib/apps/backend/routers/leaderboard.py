import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from apps.backend.dependencies import get_leaderboard_app_service, require_authenticated
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.leaderboard import (
    LeaderboardRead,
    TrendPoint,
    ModelSummary,
    ModelBenchmarkHistory,
)
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


@router.get(
    "/benchmarks/{benchmark_version_id}/leaderboard/history",
    response_model=list[TrendPoint],
    summary="Get Benchmark Version Score History",
)
def get_benchmark_version_history(
    benchmark_version_id: uuid.UUID,
    response: Response,
    claims: TokenClaims = Depends(require_authenticated),
    service: LeaderboardApplicationService = Depends(get_leaderboard_app_service),
) -> list[TrendPoint]:
    """Retrieves score evolution for all models on a specific benchmark version."""
    response.headers["Cache-Control"] = "max-age=60"
    return service.get_benchmark_history(benchmark_version_id)


@router.get(
    "/models/{model_name}/summary",
    response_model=ModelSummary,
    summary="Get Model Performance Summary",
)
def get_model_summary(
    model_name: str,
    response: Response,
    claims: TokenClaims = Depends(require_authenticated),
    service: LeaderboardApplicationService = Depends(get_leaderboard_app_service),
) -> ModelSummary:
    """Retrieves an aggregate summary of a model's performance."""
    response.headers["Cache-Control"] = "max-age=60"
    return service.get_model_summary(model_name)


@router.get(
    "/models/{model_name}/history",
    response_model=list[TrendPoint],
    summary="Get Model Score History",
)
def get_model_history(
    model_name: str,
    response: Response,
    claims: TokenClaims = Depends(require_authenticated),
    service: LeaderboardApplicationService = Depends(get_leaderboard_app_service),
) -> list[TrendPoint]:
    """Retrieves raw score evolution for a model across all evaluations."""
    response.headers["Cache-Control"] = "max-age=60"
    return service.get_model_history(model_name)


@router.get(
    "/models/{model_name}/benchmarks",
    response_model=list[ModelBenchmarkHistory],
    summary="Get Model Benchmark History",
)
def get_model_benchmark_history(
    model_name: str,
    response: Response,
    claims: TokenClaims = Depends(require_authenticated),
    service: LeaderboardApplicationService = Depends(get_leaderboard_app_service),
) -> list[ModelBenchmarkHistory]:
    """Retrieves model history grouped by Benchmark, providing continuous timelines."""
    response.headers["Cache-Control"] = "max-age=60"
    return service.get_model_benchmark_history(model_name)


@router.get(
    "/models/{model_name}/rank-history",
    response_model=list[TrendPoint],
    summary="Get Model Rank History",
)
def get_model_rank_history(
    model_name: str,
    response: Response,
    claims: TokenClaims = Depends(require_authenticated),
    service: LeaderboardApplicationService = Depends(get_leaderboard_app_service),
) -> list[TrendPoint]:
    """Retrieves historical ranking from leaderboard snapshots."""
    response.headers["Cache-Control"] = "max-age=60"
    return service.get_model_rank_history(model_name)


@router.post(
    "/benchmarks/{benchmark_version_id}/leaderboard/snapshot",
    status_code=202,
    summary="[Admin] Trigger Benchmark Snapshot Rebuild",
)
def trigger_benchmark_snapshot(
    benchmark_version_id: uuid.UUID,
    claims: TokenClaims = Depends(require_authenticated),
) -> dict[str, str]:
    """
    Manually triggers a background task to rebuild the leaderboard snapshot for a benchmark version.
    Intended for administrative and maintenance purposes only.
    """
    # In a real app, verify claims contain 'admin' role
    from apps.backend.events.celery_snapshot_dispatcher import CelerySnapshotDispatcher

    dispatcher = CelerySnapshotDispatcher()
    dispatcher.dispatch_benchmark_snapshot(benchmark_version_id, execution_id_trigger=None)
    return {"status": "accepted", "message": "Snapshot generation dispatched"}


@router.post(
    "/capabilities/{capability_id}/leaderboard/snapshot",
    status_code=202,
    summary="[Admin] Trigger Capability Snapshot Rebuild",
)
def trigger_capability_snapshot(
    capability_id: uuid.UUID,
    claims: TokenClaims = Depends(require_authenticated),
) -> dict[str, str]:
    """
    Manually triggers a background task to rebuild the leaderboard snapshot for a capability.
    Intended for administrative and maintenance purposes only.
    """
    # In a real app, verify claims contain 'admin' role
    from apps.backend.events.celery_snapshot_dispatcher import CelerySnapshotDispatcher

    dispatcher = CelerySnapshotDispatcher()
    dispatcher.dispatch_capability_snapshot(capability_id, execution_id_trigger=None)
    return {"status": "accepted", "message": "Snapshot generation dispatched"}
