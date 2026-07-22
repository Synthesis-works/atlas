from uuid import UUID

from atlas_db.models.dataset import Dataset
from fastapi import APIRouter, Depends, File, UploadFile

from ..importers.base import CSVImporter
from ..models.dtos import DatasetDTO, DatasetRegistrationRequest
from ..repositories.dataset_repo import DatasetRepository
from ..services.publishing import PublishingService
from ..services.versioning import VersioningService
from ..storage.provider import StorageProvider
from ..validation.rules import RequiredColumnsRule, UTF8EncodingRule
from ..validation.service import ValidationService
from .dependencies import (
    get_dataset_repository,
    get_publishing_service,
    get_storage_provider,
    get_validation_service,
    get_versioning_service,
)

router = APIRouter()


@router.post("/datasets", response_model=DatasetDTO)
def register_dataset(
    req: DatasetRegistrationRequest, repo: DatasetRepository = Depends(get_dataset_repository)
):
    ds = Dataset(
        registry_id=req.registry_id,
        source_id=req.source_id,
        license_id=req.license_id,
        name=req.name,
        description=req.description,
    )
    ds = repo.create_dataset(ds)
    return DatasetDTO.model_validate(ds)


@router.post("/datasets/{dataset_id}/versions")
def upload_dataset_version(
    dataset_id: UUID,
    file: UploadFile = File(...),
    storage: StorageProvider = Depends(get_storage_provider),
    versioning: VersioningService = Depends(get_versioning_service),
):
    # Determine importer based on file type (simplified)
    importer = CSVImporter(storage)

    # Store file
    dest_path = f"{dataset_id}/{file.filename}"
    stored_path = importer.import_file(file.file, dest_path)

    # Register version metadata
    version = versioning.register_version_metadata(
        dataset_id=dataset_id,
        storage_path=stored_path,
        version_number=1,  # simplified
        checksum="pending",  # would be calculated
    )
    return {"message": "Version uploaded", "version_id": version.id, "status": "UPLOADED"}


@router.post("/datasets/{dataset_id}/versions/{version_id}/validate")
def validate_version(
    dataset_id: UUID,
    version_id: UUID,
    validator: ValidationService = Depends(get_validation_service),
):
    # In reality, rules might be fetched from schema_def
    rules = [UTF8EncodingRule(), RequiredColumnsRule(["id", "text"])]
    is_valid = validator.validate_version(version_id, rules)
    return {"is_valid": is_valid}


@router.post("/datasets/{dataset_id}/versions/{version_id}/publish")
def publish_version(
    dataset_id: UUID,
    version_id: UUID,
    publisher: PublishingService = Depends(get_publishing_service),
):
    publisher.publish(version_id)
    return {"message": "Version published"}
