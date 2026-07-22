from uuid import UUID

from atlas_db.models.dataset import ValidationStatus

from ..repositories.dataset_repo import DatasetRepository
from ..storage.provider import StorageProvider
from .rules import ValidationRule


class ValidationService:
    def __init__(self, repo: DatasetRepository, storage: StorageProvider):
        self.repo = repo
        self.storage = storage

    def validate_version(self, version_id: UUID, rules: list[ValidationRule]) -> bool:
        version = self.repo.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        self.repo.update_version_status(version_id, ValidationStatus.PENDING)

        try:
            with self.storage.get(version.storage_path) as f:
                file_content = f.read()

            all_passed = True
            for rule in rules:
                result = rule.validate(file_content)
                if not result.is_valid:
                    all_passed = False
                    # In a real system, we might log these errors to a ValidationLog table
                    break

            if all_passed:
                self.repo.update_version_status(version_id, ValidationStatus.VALIDATED)
                return True
            else:
                self.repo.update_version_status(version_id, ValidationStatus.FAILED)
                return False

        except Exception:
            self.repo.update_version_status(version_id, ValidationStatus.FAILED)
            raise
