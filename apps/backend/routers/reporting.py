import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

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
    "/runs/{run_id}/export",
    summary="Export execution run report",
    description="Export detailed execution run results in JSON or CSV format.",
)
def export_run_results(
    run_id: uuid.UUID = Path(..., description="Unique ID of the execution run"),
    format: str = Query("json", pattern="^(json|csv)$", description="Export format (json or csv)"),
    include_prompt: bool = Query(False, description="Include original prompts in the export"),
    include_expected_output: bool = Query(
        False, description="Include expected outputs in the export"
    ),
    service: ReportingService = Depends(get_reporting_service),
    current_user: dict[str, Any] = Depends(require_permission("report:read")),
) -> Response:
    try:
        # Truthful agent-run context (steps, tool calls, provider chain, duration)
        # when the execution belongs to an in-memory agent task; {} otherwise.
        execution_meta = _collect_agent_execution_meta(run_id)
        document = service.build_report_export(
            run_id,
            include_prompt=include_prompt,
            include_expected_output=include_expected_output,
            execution_meta=execution_meta,
        )
        export_result = service.export_run_results(
            run_id,
            format_type=format,
            include_prompt=include_prompt,
            include_expected_output=include_expected_output,
            execution_meta=execution_meta,
            document=document,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    filename = export_result.filename_stem or f"run_{run_id}"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}.{export_result.filename_extension}"'
    }

    return Response(
        content=export_result.content,
        media_type=export_result.mime_type,
        headers=headers,
    )


def _collect_agent_execution_meta(run_id: uuid.UUID) -> dict[str, Any]:
    """Collect truthful agent-run context for an execution id when an in-memory
    agent task produced it. Returns {} when no agent task matches, so exports
    only ever include what genuinely exists."""
    from apps.backend.routers.agent import _agent_tasks_db

    run_id_str = str(run_id)
    for task in _agent_tasks_db.values():
        if run_id_str not in task.execution_ids:
            continue

        providers: list[str] = []
        if task.primary_provider:
            providers.append(task.primary_provider)
        for trace_event in task.execution_trace:
            details = trace_event.details or {}
            if trace_event.event_type.startswith("provider_decision_"):
                provider = details.get("provider")
                if provider and str(provider) not in providers:
                    providers.append(str(provider))
            elif trace_event.event_type == "provider_fallback":
                next_provider = details.get("next_provider")
                if (
                    next_provider
                    and str(next_provider) != "NONE"
                    and str(next_provider) not in providers
                ):
                    providers.append(str(next_provider))

        meta: dict[str, Any] = {
            "steps": task.step_count,
            "tool_calls": task.total_tool_calls,
            "provider_chain": providers,
        }
        if task.started_at and task.completed_at:
            delta = task.completed_at - task.started_at
            if delta.total_seconds() >= 0:
                meta["duration_seconds"] = delta.total_seconds()
        return meta

    return {}


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
