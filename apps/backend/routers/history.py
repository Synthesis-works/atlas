from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.backend.dependencies import (
    TokenClaims,
    get_benchmark_app_service,
    get_db_session,
    get_execution_app_service,
    require_authenticated,
)
from apps.backend.schemas.benchmarks import BenchmarkRead
from apps.backend.schemas.executions import ExecutionHistoryRead, ModelActivityRead
from apps.backend.schemas.responses import APIResponse
from apps.backend.services.benchmarks import BenchmarkApplicationService
from apps.backend.services.executions import ExecutionApplicationService
from services.search.service import resolve_accessible_project_ids

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/benchmarks/recent", response_model=APIResponse[list[BenchmarkRead]])
def list_recent_benchmarks(
    limit: int = 10,
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session),
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service),
):
    """
    Returns the most recently published benchmarks scoped to the authenticated
    user's accessible projects.
    "Recent" is defined as benchmarks with status="published", ordered by their last updated timestamp (`updated_at`) in descending order.
    """
    project_ids = resolve_accessible_project_ids(db, claims.sub)
    benchmarks = app_service.get_recent_benchmarks(limit=limit, project_ids=project_ids)
    return APIResponse.success_response(data=benchmarks)


@router.get("/executions/recent", response_model=APIResponse[list[ExecutionHistoryRead]])
def list_recent_executions(
    limit: int = 10,
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session),
    app_service: ExecutionApplicationService = Depends(get_execution_app_service),
):
    """
    Returns the most recent executions scoped to the authenticated user's
    accessible projects.
    "Recent" is defined as executions ordered by their creation timestamp (`created_at`) in descending order.
    """
    project_ids = resolve_accessible_project_ids(db, claims.sub)
    executions = app_service.get_recent_executions(limit=limit, project_ids=project_ids)
    return APIResponse.success_response(data=executions)


@router.get("/models/recent", response_model=APIResponse[list[ModelActivityRead]])
def list_recent_models(
    limit: int = 10,
    claims: TokenClaims = Depends(require_authenticated),
    db: Session = Depends(get_db_session),
    app_service: ExecutionApplicationService = Depends(get_execution_app_service),
):
    """
    Returns the most recently active target models scoped to the authenticated
    user's accessible projects.
    "Recent" is defined as unique target_models ordered by their latest execution timestamp in descending order.
    """
    project_ids = resolve_accessible_project_ids(db, claims.sub)
    models = app_service.get_recent_models(limit=limit, project_ids=project_ids)
    return APIResponse.success_response(data=models)
