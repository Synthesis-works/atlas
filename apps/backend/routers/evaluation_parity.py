import uuid

from atlas_db.models.core import OrganizationRole
from fastapi import APIRouter, Depends, HTTPException, Path, status

from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service
from apps.backend.dependencies import (
    get_evaluation_parity_service,
    require_authenticated,
)
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.evaluation import (
    EvaluationResultsRead,
    ExecutionCompareRequest,
    ExecutionCompareResponse,
)
from apps.backend.schemas.evaluation_cases import (
    EvaluationCaseCreate,
    EvaluationCaseWriteResponse,
)
from apps.backend.schemas.reports import ReportCreate, ReportListRead, ReportRead
from apps.backend.services.evaluation_parity import EvaluationParityService

router = APIRouter(tags=["evaluation-parity"])

WRITE_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
]
READ_ROLES = [
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.MEMBER,
    OrganizationRole.VIEWER,
]


@router.get(
    "/projects/{project_id}/executions/{execution_id}/evaluation-results",
    response_model=EvaluationResultsRead,
)
def get_evaluation_results(
    project_id: uuid.UUID = Path(...),
    execution_id: uuid.UUID = Path(...),
    service: EvaluationParityService = Depends(get_evaluation_parity_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    authz_service.authorize_project_access(
        project_id=project_id, user_id=claims.sub, allowed_roles=READ_ROLES
    )
    result = service.get_evaluation_results(project_id, execution_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found in this project."
        )
    return result


@router.post(
    "/projects/{project_id}/datasets/{dataset_id}/evaluation-cases",
    response_model=EvaluationCaseWriteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation_cases(
    payload: EvaluationCaseCreate,
    project_id: uuid.UUID = Path(...),
    dataset_id: uuid.UUID = Path(...),
    service: EvaluationParityService = Depends(get_evaluation_parity_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    authz_service.authorize_project_access(
        project_id=project_id, user_id=claims.sub, allowed_roles=WRITE_ROLES
    )
    result = service.create_evaluation_cases(project_id, dataset_id, payload.evaluation_cases)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found in this project."
        )
    return result


@router.post(
    "/projects/{project_id}/executions/compare",
    response_model=ExecutionCompareResponse,
)
def compare_executions(
    payload: ExecutionCompareRequest,
    project_id: uuid.UUID = Path(...),
    service: EvaluationParityService = Depends(get_evaluation_parity_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    authz_service.authorize_project_access(
        project_id=project_id, user_id=claims.sub, allowed_roles=READ_ROLES
    )
    return service.compare_executions(project_id, payload.execution_ids)


@router.post(
    "/projects/{project_id}/reports",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_report(
    payload: ReportCreate,
    project_id: uuid.UUID = Path(...),
    service: EvaluationParityService = Depends(get_evaluation_parity_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    member = authz_service.authorize_project_access(
        project_id=project_id, user_id=claims.sub, allowed_roles=WRITE_ROLES
    )
    report = service.generate_report(
        project_id=project_id,
        created_by_id=member.id,
        title=payload.title,
        benchmark_id=payload.benchmark_id,
        execution_id=payload.execution_id,
        version_string=payload.version_string,
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provided execution not found in this project.",
        )
    return report


@router.get("/projects/{project_id}/reports", response_model=ReportListRead)
def list_reports(
    project_id: uuid.UUID = Path(...),
    service: EvaluationParityService = Depends(get_evaluation_parity_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    authz_service.authorize_project_access(
        project_id=project_id, user_id=claims.sub, allowed_roles=READ_ROLES
    )
    reports = service.list_reports(project_id)
    return ReportListRead(project_id=project_id, reports=reports, total=len(reports))
