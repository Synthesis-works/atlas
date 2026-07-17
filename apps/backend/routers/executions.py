import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from apps.backend.dependencies import get_db_session, get_current_user
from apps.backend.schemas.executions import ExecutionCreate, ExecutionResponse
from apps.backend.services.executions import ExecutionService
from apps.backend.authz import ProjectAuthorizationService
from apps.backend.worker.tasks import run_execution_task
from apps.backend.worker.celery_app import celery_app
from atlas_db.models.core import User
from atlas_db.models.execution import ExecutionStatus

router = APIRouter(prefix="/projects/{project_id}/executions", tags=["executions"])

@router.post("", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
def create_execution(
    project_id: uuid.UUID,
    execution_in: ExecutionCreate,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a new benchmark execution.
    """
    # Enforce RBAC: Member or Admin can execute
    member = ProjectAuthorizationService.authorize_project_access(
        db, current_user.id, project_id, required_roles=["OWNER", "ADMIN", "MEMBER"]
    )
    
    execution = ExecutionService.create_execution(
        db=db,
        project_id=project_id,
        execution_in=execution_in,
        submitted_by_id=member.id
    )

    # Dispatch to Celery, preserving correlation ID
    correlation_id = getattr(request.state, "correlation_id", None)
    task = run_execution_task.delay(str(execution.id), correlation_id=correlation_id)
    
    # Save the celery_task_id to the execution model
    execution.celery_task_id = task.id
    db.commit()

    return execution

@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
def cancel_execution(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Cooperatively cancel a running execution.
    """
    # Enforce RBAC
    ProjectAuthorizationService.authorize_project_access(
        db, current_user.id, project_id, required_roles=["OWNER", "ADMIN", "MEMBER"]
    )

    execution = ExecutionService.get_execution(db, project_id, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = ExecutionService.cancel_execution(db, execution)
    
    # If the task is just queued, we can forcefully revoke it in celery
    if execution.celery_task_id:
        celery_app.control.revoke(execution.celery_task_id, terminate=False)
        
    return execution

@router.get("", response_model=List[ExecutionResponse])
def list_executions(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    List executions for a project. Viewers can also read.
    """
    ProjectAuthorizationService.authorize_project_access(
        db, current_user.id, project_id, required_roles=["OWNER", "ADMIN", "MEMBER", "VIEWER"]
    )
    return ExecutionService.list_executions_for_project(db, project_id, skip, limit)

@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific execution.
    """
    ProjectAuthorizationService.authorize_project_access(
        db, current_user.id, project_id, required_roles=["OWNER", "ADMIN", "MEMBER", "VIEWER"]
    )
    
    execution = ExecutionService.get_execution(db, execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    return execution

@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
def cancel_execution(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a queued or running execution.
    """
    ProjectAuthorizationService.authorize_project_access(
        db, current_user.id, project_id, required_roles=["OWNER", "ADMIN", "MEMBER"]
    )
    
    execution = ExecutionService.get_execution(db, execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    return ExecutionService.update_status(db, execution, ExecutionStatus.CANCELLED)
