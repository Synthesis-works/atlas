import uuid
from fastapi import HTTPException, status

from atlas_db.models.dataset import DatasetVersion, DatasetLifecycle
from atlas_db.repositories.dataset import DatasetVersionRepository

class PublishingService:
    def __init__(self, version_repo: DatasetVersionRepository):
        self.version_repo = version_repo

    def publish_dataset_version(self, version_id: uuid.UUID) -> DatasetVersion:
        version = self.version_repo.get(version_id)
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset version not found")
            
        if version.lifecycle == DatasetLifecycle.PUBLISHED:
            return version
            
        if version.lifecycle != DatasetLifecycle.VALID:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Version must be VALID to be published")
            
        version.lifecycle = DatasetLifecycle.PUBLISHED
        self.version_repo.update(version)
        return version
