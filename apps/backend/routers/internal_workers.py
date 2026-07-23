import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from apps.backend.dependencies import get_db_session
from apps.backend.worker_auth import require_worker_auth
from packages.execution_engine.api.worker_dtos import (
    AcquireRequest,
    AcquireResponse,
    CompleteFailureRequest,
    CompleteSuccessRequest,
    HeartbeatRequest,
    HeartbeatResponse,
)
from packages.execution_engine.application.worker_app_service import WorkerApplicationService
from packages.execution_engine.domain.services import ExecutionService
from packages.execution_engine.persistence.repository import SqlAlchemyExecutionRepository

workers_router = APIRouter(tags=["Internal Workers"], dependencies=[Depends(require_worker_auth)])


def get_worker_service(db: Session = Depends(get_db_session)) -> WorkerApplicationService:
    domain_service = ExecutionService()
    execution_repo = SqlAlchemyExecutionRepository(db)
    return WorkerApplicationService(domain_service, execution_repo)


@workers_router.post("/acquire", response_model=AcquireResponse)
def acquire_work(
    request: AcquireRequest,
    response: Response,
    service: WorkerApplicationService = Depends(get_worker_service),
):
    grant = service.acquire_work(request.worker_id)
    if not grant:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    return grant


@workers_router.post("/executions/{execution_id}/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    execution_id: uuid.UUID,
    request: HeartbeatRequest,
    service: WorkerApplicationService = Depends(get_worker_service),
):
    new_expiration = service.heartbeat(execution_id, request.worker_id)
    return HeartbeatResponse(execution_id=execution_id, lease_expires_at=new_expiration)


@workers_router.post("/executions/{execution_id}/complete_success", status_code=status.HTTP_200_OK)
def complete_success(
    execution_id: uuid.UUID,
    request: CompleteSuccessRequest,
    service: WorkerApplicationService = Depends(get_worker_service),
):
    service.complete_success(
        execution_id=execution_id, worker_id=request.worker_id, artifacts=request.artifacts
    )
    return {"message": "success"}


@workers_router.post("/executions/{execution_id}/complete_failure", status_code=status.HTTP_200_OK)
def complete_failure(
    execution_id: uuid.UUID,
    request: CompleteFailureRequest,
    service: WorkerApplicationService = Depends(get_worker_service),
):
    service.complete_failure(
        execution_id=execution_id,
        worker_id=request.worker_id,
        error_message=request.error_message,
        artifacts=request.artifacts,
    )
    return {"message": "failure logged"}
