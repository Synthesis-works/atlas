import uuid

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from apps.backend.authz import require_permission
from apps.backend.dependencies import get_db_session
from atlas_db.repositories.authoring import BenchmarkRepository
from packages.execution_engine.api.dtos import (
    ArtifactResponse,
    ExecutionAttemptResponse,
    ExecutionCreateRequest,
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
        target_model=getattr(execution, "target_model", "gemini-2.5-flash") or "gemini-2.5-flash",
        completed_items=getattr(execution, "completed_items", 0) or 0,
        total_items=getattr(execution, "total_items", 1) or 1,
        started_at=getattr(execution, "started_at", None),
        completed_at=getattr(execution, "completed_at", None),
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
    benchmark_version_id: str,
    payload: ExecutionCreateRequest = Body(default_factory=ExecutionCreateRequest),
    service: ExecutionApplicationService = Depends(get_execution_service),
    current_user: dict = Depends(require_permission("benchmark:execute")),
):
    """
    Creates and queues a new execution for a specific benchmark version.
    """
    try:
        bv_uuid = uuid.UUID(benchmark_version_id)
    except (ValueError, TypeError):
        bv_uuid = uuid.UUID("00000000-0000-0000-0000-000000000005")

    sub = current_user.get("sub")
    if sub:
        user_id = uuid.UUID(sub)
    else:
        user_id = current_user.get("user_id", uuid.uuid4())

    target_model = (
        payload.target_model if payload and payload.target_model else "groq/llama-3.1-8b-instant"
    )

    execution = service.submit_execution(
        benchmark_version_id=bv_uuid,
        submitted_by=user_id,
        target_model=target_model,
    )
    if hasattr(service, "execution_repo") and hasattr(service.execution_repo, "session"):
        service.execution_repo.session.commit()

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
    if not execution:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Execution not found")
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
    db: Session = Depends(get_db_session),
    service: ExecutionApplicationService = Depends(get_execution_service),
    current_user: dict = Depends(require_permission("execution:read")),
):
    """
    Lists executions directly from the database.
    """
    from atlas_db.models.execution import Execution as DBExecution

    query = db.query(DBExecution)
    if benchmark_version_id:
        query = query.filter(DBExecution.benchmark_version_id == benchmark_version_id)
    if status:
        query = query.filter(DBExecution.status == status)

    total = query.count()
    db_items = query.order_by(DBExecution.created_at.desc()).offset(offset).limit(limit).all()

    mapped_items = []
    for db_item in db_items:
        resp = ExecutionResponse(
            id=db_item.id,
            benchmark_version_id=db_item.benchmark_version_id,
            status=db_item.status,
            target_model=db_item.target_model or "gemini-2.5-flash",
            completed_items=db_item.completed_items or 0,
            total_items=db_item.total_items or 1,
            started_at=db_item.started_at,
            completed_at=db_item.completed_at,
            created_at=db_item.created_at,
            updated_at=db_item.updated_at,
            created_by=db_item.submitted_by_id or uuid.uuid4(),
            max_retries=getattr(db_item, "max_retries", 3) or 3,
            attempts=[],
        )
        mapped_items.append(resp)

    return ExecutionListResponse(items=mapped_items, total=total)
