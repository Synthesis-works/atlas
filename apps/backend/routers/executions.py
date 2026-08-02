import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from apps.backend.authz import require_permission
from apps.backend.dependencies import get_db_session
from atlas_db.repositories.authoring import BenchmarkRepository
from packages.execution_engine.api.dtos import (
    ArtifactResponse,
    ExecutionAttemptResponse,
    ExecutionListResponse,
    ExecutionResponse,
)
from packages.execution_engine.application.execution_app_service import ExecutionApplicationService
from packages.execution_engine.domain.models import Execution
from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.persistence.repository import SqlAlchemyExecutionRepository

benchmark_executions_router = APIRouter(tags=["Executions"])
executions_router = APIRouter(tags=["Executions"])


def get_execution_service(db: Session = Depends(get_db_session)) -> ExecutionApplicationService:
    domain_service = ExecutionService()
    execution_repo = SqlAlchemyExecutionRepository(db)
    benchmark_repo = BenchmarkRepository(db)
    return ExecutionApplicationService(domain_service, execution_repo, benchmark_repo)


def map_to_response(execution: Execution) -> ExecutionResponse:
    return ExecutionResponse(
        id=execution.id,
        benchmark_version_id=execution.benchmark_version_id,
        status=execution.status,
        created_at=execution.created_at,
        updated_at=execution.updated_at,
        created_by=execution.created_by,
        max_retries=execution.max_retries,
        attempts=[
            ExecutionAttemptResponse(
                id=a.id,
                attempt_number=a.attempt_number,
                status=a.status,
                started_at=a.started_at,
                finished_at=a.finished_at,
                error_message=a.error_message,
                artifacts=[
                    ArtifactResponse(id=art.id, type=art.type, storage_uri=art.storage_uri)
                    for art in a.artifacts
                ],
            )
            for a in execution.attempts
        ],
    )


@benchmark_executions_router.post(
    "/benchmarks/{benchmark_version_id}/executions",
    response_model=ExecutionResponse,
    status_code=201,
)
def create_execution(
    benchmark_version_id: uuid.UUID,
    service: ExecutionApplicationService = Depends(get_execution_service),
    current_user: dict = Depends(require_permission("benchmark:execute")),
):
    """
    Creates and queues a new execution for a specific benchmark version.
    """
    user_id = current_user.get("user_id", uuid.uuid4())
    execution = service.submit_execution(benchmark_version_id, user_id)
    return map_to_response(execution)


@executions_router.get("/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(
    execution_id: uuid.UUID,
    service: ExecutionApplicationService = Depends(get_execution_service),
    current_user: dict = Depends(require_permission("execution:read")),
):
    """
    Retrieves details of an execution including attempts, leases, and artifacts.
    """
    execution = service.get_execution(execution_id)
    return map_to_response(execution)


@executions_router.post("/executions/{execution_id}/cancel", response_model=ExecutionResponse)
def cancel_execution(
    execution_id: uuid.UUID,
    service: ExecutionApplicationService = Depends(get_execution_service),
    current_user: dict = Depends(require_permission("execution:cancel")),
):
    """
    Cancels a running or queued execution.
    """
    execution = service.cancel_execution(execution_id)
    return map_to_response(execution)


@executions_router.get("/executions", response_model=ExecutionListResponse)
def list_executions(
    benchmark_version_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ExecutionApplicationService = Depends(get_execution_service),
    current_user: dict = Depends(require_permission("execution:read")),
):
    """
    Lists executions. Note: In a real app, this needs a DB query that returns multiple executions.
    For this slice, it is stubbed to satisfy the OpenAPI schema.
    """
    # Just a stub for the OpenAPI. The actual repository would need a find_all method.
    return ExecutionListResponse(items=[], total=0)
