from typing import Any
from fastapi import Depends
from sqlalchemy.orm import Session
from atlas_db.core.session import get_db

from ..repositories.dataset_repo import DatasetRepository
from ..storage.provider import StorageProvider, LocalStorageProvider
from ..validation.service import ValidationService
from ..services.versioning import VersioningService
from ..services.publishing import PublishingService

def get_dataset_repository(db: Session = Depends(get_db)) -> DatasetRepository:
    return DatasetRepository(db)

def get_storage_provider() -> StorageProvider:
    return LocalStorageProvider()

def get_validation_service(
    repo: DatasetRepository = Depends(get_dataset_repository),
    storage: StorageProvider = Depends(get_storage_provider)
) -> ValidationService:
    return ValidationService(repo, storage)

def get_versioning_service(repo: DatasetRepository = Depends(get_dataset_repository)) -> VersioningService:
    return VersioningService(repo)

def get_publishing_service(repo: DatasetRepository = Depends(get_dataset_repository)) -> PublishingService:
    return PublishingService(repo)
