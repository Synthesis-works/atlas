import uuid
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from apps.backend.dependencies import get_db_session, get_current_user
from apps.backend.schemas.evaluation import CapabilityProfileRead
from apps.backend.services.evaluation import EvaluationService
from apps.backend.authz import ProjectAuthorizationService
from atlas_db.models.core import User

router = APIRouter(prefix="/projects/{project_id}/executions/{execution_id}", tags=["evaluation"])

@router.post("/evaluate", response_model=CapabilityProfileRead, status_code=status.HTTP_200_OK)
def evaluate_execution(
    project_id: uuid.UUID,
    execution_id: uuid.UUID,
    force: bool = Query(False, description="Force recompute of the evaluation even if it exists"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluates a completed execution synchronously.
    Requires OWNER, ADMIN, or MEMBER roles on the project.
    """
    # 1. Authorize (Write operation so OWNER, ADMIN, MEMBER only)
    authz = ProjectAuthorizationService(db)
    if not authz.authorize_project_access(current_user, project_id, required_roles=["OWNER", "ADMIN", "MEMBER"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to evaluate executions in this project."
        )

    # 2. Evaluate
    eval_service = EvaluationService(db)
    
    # Validation of project_id vs execution_id is normally handled, but let's be sure it belongs to the project
    execution = eval_service.execution_repo.get(execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found in this project.")

    try:
        profile = eval_service.evaluate_execution(execution_id, force=force)
        db.commit()
        return profile
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
