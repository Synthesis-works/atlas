from fastapi import APIRouter, Depends

from apps.backend.dependencies import get_benchmark_app_service
from apps.backend.schemas.benchmarks import BenchmarkRead
from apps.backend.schemas.responses import APIResponse
from apps.backend.services.benchmarks import BenchmarkApplicationService

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/benchmarks/recent", response_model=APIResponse[list[BenchmarkRead]])
def list_recent_benchmarks(
    limit: int = 10,
    app_service: BenchmarkApplicationService = Depends(get_benchmark_app_service),
):
    """
    Returns the most recently published benchmarks globally.
    "Recent" is defined as benchmarks with status="published", ordered by their last updated timestamp (`updated_at`) in descending order.
    """
    benchmarks = app_service.get_recent_benchmarks(limit=limit)
    return APIResponse.success_response(data=benchmarks)


from apps.backend.dependencies import get_execution_app_service
from apps.backend.services.executions import ExecutionApplicationService
from apps.backend.schemas.executions import ExecutionHistoryRead, ModelActivityRead


@router.get("/executions/recent", response_model=APIResponse[list[ExecutionHistoryRead]])
def list_recent_executions(
    limit: int = 10,
    app_service: ExecutionApplicationService = Depends(get_execution_app_service),
):
    """
    Returns the most recent executions globally.
    "Recent" is defined as executions ordered by their creation timestamp (`created_at`) in descending order.
    """
    executions = app_service.get_recent_executions(limit=limit)
    return APIResponse.success_response(data=executions)


@router.get("/models/recent", response_model=APIResponse[list[ModelActivityRead]])
def list_recent_models(
    limit: int = 10,
    app_service: ExecutionApplicationService = Depends(get_execution_app_service),
):
    """
    Returns the most recently active target models globally.
    "Recent" is defined as unique target_models ordered by their latest execution timestamp in descending order.
    """
    models = app_service.get_recent_models(limit=limit)
    return APIResponse.success_response(data=models)
