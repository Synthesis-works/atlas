from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ...models.dtos import (
    CapabilityDashboardDTO,
    LeaderboardResponseDTO,
    PaginatedHistoryResponseDTO,
    SystemHealthDTO,
    VersionInfoDTO,
)
from ...services.reporting import ReportingService
from ..dependencies import get_reporting_service

router = APIRouter()


@router.get("/health", response_model=SystemHealthDTO)
def get_health():
    return SystemHealthDTO(status="ok", timestamp=datetime.utcnow())


@router.get("/versions", response_model=VersionInfoDTO)
def get_versions():
    return VersionInfoDTO(service="reporting-service", version="1.0.0")


@router.get("/dashboard")
def get_dashboard():
    # Placeholder for a high-level project dashboard
    return {"message": "Dashboard data"}


@router.get("/summary")
def get_summary():
    return {"message": "Summary data"}


@router.get("/capabilities/{model_identifier}", response_model=CapabilityDashboardDTO)
def get_capabilities(
    model_identifier: str, service: ReportingService = Depends(get_reporting_service)
):
    read_model = service.get_capability_dashboard(model_identifier)
    if not read_model:
        raise HTTPException(status_code=404, detail="Capability profile not found for model")

    return CapabilityDashboardDTO.model_validate(read_model)


@router.get("/leaderboards", response_model=LeaderboardResponseDTO)
def get_leaderboards(
    strategy: str = Query("overall", description="The ranking strategy"),
    limit: int = Query(10, ge=1, le=100),
    service: ReportingService = Depends(get_reporting_service),
):
    read_model = service.get_leaderboard(strategy_name=strategy, limit=limit)
    return LeaderboardResponseDTO.model_validate(read_model)


@router.get("/history", response_model=PaginatedHistoryResponseDTO)
def get_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ReportingService = Depends(get_reporting_service),
):
    items, total = service.get_history(limit=limit, offset=offset)

    # Map read models to DTOs
    # The PaginatedHistoryResponseDTO model validation could handle this,
    # but constructing it explicitly ensures clear boundary.
    return PaginatedHistoryResponseDTO(
        items=items,  # type: ignore # Pydantic will coerce HistoryEntryRead to HistoryEntryDTO
        total=total,
        page=(offset // limit) + 1,
        size=limit,
    )


# Placeholders for others:
@router.get("/models/{model_identifier}")
def get_model_report(model_identifier: str):
    pass


@router.get("/benchmarks/{benchmark_id}")
def get_benchmark_report(benchmark_id: str):
    pass
