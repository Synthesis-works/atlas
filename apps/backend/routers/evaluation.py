import uuid

from atlas_db.models.core import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from apps.backend.authz import ProjectAuthorizationService
from apps.backend.dependencies import get_current_user, get_db_session
from apps.backend.schemas.evaluation import CapabilityProfileRead, EvaluationEnqueuedResponse
from apps.backend.services.evaluation import EvaluationService

router = APIRouter(prefix="/projects/{project_id}/executions/{execution_id}", tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluationEnqueuedResponse, status_code=status.HTTP_202_ACCEPTED)
def evaluate_execution(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Enqueues a background evaluation for a completed execution.
    Requires OWNER, ADMIN, or MEMBER roles on the project.
    """
    # 1. Authorize (Write operation so OWNER, ADMIN, MEMBER only)
    authz = ProjectAuthorizationService(db)
    if not authz.authorize_project_access(
        current_user, project_id, required_roles=["OWNER", "ADMIN", "MEMBER"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to evaluate executions in this project.",
        )

    # 2. Evaluate
    eval_service = EvaluationService(db)

    # Validation of project_id vs execution_id is normally handled, but let's be sure it belongs to the project
    execution = eval_service.execution_repo.get(execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found in this project."
        )

    try:
        from apps.backend.worker.evaluation_tasks import run_evaluation_task
        run_evaluation_task.delay(str(execution_id))
        return EvaluationEnqueuedResponse(execution_id=execution_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
