import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from apps.backend.authz import require_permission
from apps.backend.dependencies import get_reporting_service
from apps.backend.schemas.reporting import (
    CapabilityDashboardRead,
    PaginatedReportRunsRead,
    ReportSummaryRead,
)
from services.report.models.read_models import ReportRunsFilter, ReportRunStatus
from services.report.services.reporting import ReportingService

router = APIRouter(prefix="/reports", tags=["reporting"])


@router.get(
    "/runs",
    response_model=PaginatedReportRunsRead,
    status_code=status.HTTP_200_OK,
    summary="List execution run reports",
    description="Retrieve a paginated list of execution run summaries with optional filtering by status, benchmark, or target model.",
)
def list_report_runs(
    status: ReportRunStatus | None = Query(None, description="Filter runs by evaluation status"),
    benchmark_id: uuid.UUID | None = Query(None, description="Filter runs by benchmark ID"),
    benchmark_version: str | None = Query(
        None, description="Filter runs by benchmark version string"
    ),
    target_model: str | None = Query(None, description="Filter runs by target model name"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: dict[str, Any] = Depends(require_permission("report:read")),
) -> PaginatedReportRunsRead:
    filter_obj = ReportRunsFilter(
        status=status,
        benchmark_id=benchmark_id,
        benchmark_version=benchmark_version,
        target_model=target_model,
        limit=limit,
        offset=offset,
    )
    result = service.get_runs_filtered(filter_obj)
    return PaginatedReportRunsRead.model_validate(result, from_attributes=True)


@router.get(
    "/runs/{run_id}",
    response_model=ReportSummaryRead,
    status_code=status.HTTP_200_OK,
    summary="Get execution run report summary",
    description="Retrieve detailed reporting summary and capability score breakdown for a specific execution run.",
)
def get_run_summary(
    run_id: uuid.UUID = Path(..., description="Unique ID of the execution run"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: dict[str, Any] = Depends(require_permission("report:read")),
) -> ReportSummaryRead:
    summary = service.get_run_summary(run_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report summary for execution run '{run_id}' not found.",
        )
    return ReportSummaryRead.model_validate(summary, from_attributes=True)


@router.get(
    "/models/{model_identifier}/capabilities",
    response_model=CapabilityDashboardRead,
    status_code=status.HTTP_200_OK,
    summary="Get model capability dashboard",
    description="Retrieve aggregated capability scores and overall evaluation performance for a specific target model.",
)
def get_model_capabilities(
    model_identifier: str = Path(..., description="Unique identifier or name of the target model"),
    service: ReportingService = Depends(get_reporting_service),
    current_user: dict[str, Any] = Depends(require_permission("report:read")),
) -> CapabilityDashboardRead:
    dashboard = service.get_capability_dashboard(model_identifier)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability profile for model '{model_identifier}' not found.",
        )
    return CapabilityDashboardRead.model_validate(dashboard, from_attributes=True)
