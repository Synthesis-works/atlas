import os
import uuid

from atlas_db.models.core import OrganizationRole
from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import FileResponse

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


from apps.backend.schemas.datasets import DatasetExportResponse
from packages.datasets.services.export_action_service import ExportActionService
from packages.datasets.services.export_service import DatasetExportService
from atlas_db.services.dataset_extraction import DatasetExtractionService
from packages.datasets.infrastructure.artifact_store import LocalTrainingArtifactStore
from apps.backend.config import settings
from atlas_db.core.session import SessionLocal
from sqlalchemy.orm import Session
from apps.backend.dependencies import get_db_session
from apps.backend.worker.dataset_tasks import run_dataset_export_task

@router.post("/{dataset_id}/exports", response_model=DatasetExportResponse, status_code=status.HTTP_202_ACCEPTED)
def export_dataset_async(
    project_id: uuid.UUID = Path(...),
    dataset_id: uuid.UUID = Path(...),
    dataset_service: DatasetService = Depends(get_dataset_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    db: Session = Depends(get_db_session)
):
    # 1. Project level zero-trust authorization
    authz_service.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.MEMBER,
        ],
    )

    # 2. Strict dataset validation bounds
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    try:
        from atlas_db.services.dataset_extraction import DatasetExtractionService
        extraction_service = DatasetExtractionService(db)

        artifact_store_path = getattr(settings, "artifact_storage_path", "/tmp/atlas_artifacts")
        artifact_store = LocalTrainingArtifactStore(base_dir=artifact_store_path)

        export_service = DatasetExportService(extraction_service, artifact_store)
        action_service = ExportActionService(db, export_service)

        action = action_service.schedule_export(
            dataset_version_id=dataset.versions[0].id,
            project_id=project_id,
            user_id=claims.sub
        )
        run_dataset_export_task.delay(str(action.id))
        return action
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{dataset_id}/exports", response_model=list[DatasetExportResponse])
def list_dataset_exports(
    project_id: uuid.UUID = Path(...),
    dataset_id: uuid.UUID = Path(...),
    dataset_service: DatasetService = Depends(get_dataset_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    db: Session = Depends(get_db_session)
):
    authz_service.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER, OrganizationRole.VIEWER],
    )
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    from atlas_db.models.dataset import DatasetExportAction
    exports = db.query(DatasetExportAction).filter(
        DatasetExportAction.project_id == project_id,
        DatasetExportAction.dataset_version_id.in_([v.id for v in dataset.versions])
    ).order_by(DatasetExportAction.created_at.desc()).all()
    return exports

@router.get("/{dataset_id}/exports/{export_id}", response_model=DatasetExportResponse)
def get_dataset_export(
    project_id: uuid.UUID = Path(...),
    dataset_id: uuid.UUID = Path(...),
    export_id: uuid.UUID = Path(...),
    dataset_service: DatasetService = Depends(get_dataset_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    db: Session = Depends(get_db_session)
):
    authz_service.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER, OrganizationRole.VIEWER],
    )
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    from atlas_db.models.dataset import DatasetExportAction
    export = db.query(DatasetExportAction).filter(DatasetExportAction.id == export_id).first()
    if not export or export.project_id != project_id or export.dataset_version_id not in [v.id for v in dataset.versions]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    return export

@router.get("/{dataset_id}/exports/{export_id}/download")
def download_dataset_export(
    project_id: uuid.UUID = Path(...),
    dataset_id: uuid.UUID = Path(...),
    export_id: uuid.UUID = Path(...),
    dataset_service: DatasetService = Depends(get_dataset_service),
    claims: TokenClaims = Depends(require_authenticated),
    authz_service: ProjectAuthorizationService = Depends(get_project_authz_service),
    db: Session = Depends(get_db_session)
):
    authz_service.authorize_project_access(
        project_id=project_id,
        user_id=claims.sub,
        allowed_roles=[OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER, OrganizationRole.VIEWER],
    )
    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset or dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    from atlas_db.models.dataset import DatasetExportAction
    export = db.query(DatasetExportAction).filter(DatasetExportAction.id == export_id).first()
    if not export or export.project_id != project_id or export.dataset_version_id not in [v.id for v in dataset.versions]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    if str(export.status.value).lower() != "completed" or not export.artifact_uri:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Export is not completed")

    artifact_store_path = getattr(settings, "artifact_storage_path", "/tmp/atlas_artifacts")
    artifact_store = LocalTrainingArtifactStore(base_dir=artifact_store_path)

    try:
        file_path = artifact_store.resolve_uri(export.artifact_uri)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file missing")
        return FileResponse(file_path, filename=os.path.basename(file_path))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid artifact URI internally configured.")
