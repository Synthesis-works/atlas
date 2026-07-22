import uuid

from atlas_db.models.core import OrganizationRole
from fastapi import APIRouter, Depends, HTTPException, Path, status

from apps.backend.authz import ProjectAuthorizationService, get_project_authz_service

# We'll need get_dataset_service in dependencies.py
from apps.backend.dependencies import get_dataset_service, require_authenticated
from apps.backend.schemas.auth import TokenClaims
from apps.backend.schemas.datasets import DatasetCreate, DatasetRead
from apps.backend.services.datasets import DatasetService

router = APIRouter(prefix="/projects/{project_id}/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetRead])
def list_datasets(
    project_id: uuid.UUID = Path(...),
    limit: int = 100,
    offset: int = 0,
    dataset_service: DatasetService = Depends(get_dataset_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    authz_service.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.MEMBER,
            OrganizationRole.VIEWER,
        ],
    )
    return dataset_service.list_datasets(project_id, skip=offset, limit=limit)


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
def create_dataset(
    data: DatasetCreate,
    project_id: uuid.UUID = Path(...),
    dataset_service: DatasetService = Depends(get_dataset_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    member = authz_service.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER],
    )
    return dataset_service.create_dataset(project_id, member.id, data)


@router.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(
    dataset_id: uuid.UUID = Path(...),
    project_id: uuid.UUID = Path(...),
    dataset_service: DatasetService = Depends(get_dataset_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
):
    authz_service.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.MEMBER,
            OrganizationRole.VIEWER,
        ],
    )
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset
