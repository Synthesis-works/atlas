import hashlib
from uuid import UUID
from typing import Optional
from atlas_db.models.dataset import DatasetVersion
from ..repositories.dataset_repo import DatasetRepository

class VersioningService:
    """
    Manages semantic versions, checksums, and lineage.
    Never moves or modifies actual files.
    """
    def __init__(self, repo: DatasetRepository):
        self.repo = repo

    def calculate_checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def register_version_metadata(self, dataset_id: UUID, storage_path: str, version_number: int, checksum: str) -> DatasetVersion:
        new_version = DatasetVersion(
            dataset_id=dataset_id,
            version_string=f"v{version_number}.0",
            version_number=version_number,
            storage_path=storage_path,
            checksum=checksum
        )
        return self.repo.create_version(new_version)
        
    def update_checksum(self, version_id: UUID, checksum: str) -> None:
        self.repo.update_version_checksum(version_id, checksum)
