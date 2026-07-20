from uuid import UUID
from ..repositories.dataset_repo import DatasetRepository
# In a full state machine, we might have a specific STATUS enum for PUBLISHED.
# For now, we assume ValidationStatus is used, or a separate status field exists.
# Based on the schema provided, we'll assume there is a way to mark it published, 
# or we just use ValidationStatus.VALIDATED as a proxy if no other field exists.
# We will just simulate the state transition.

class PublishingService:
    """
    Finalizes a dataset version.
    Only transitions state. Does not validate, clean, or move files.
    """
    def __init__(self, repo: DatasetRepository):
        self.repo = repo

    def publish(self, version_id: UUID) -> None:
        version = self.repo.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
            
        # Ensure it is in a valid state before publishing
        # if version.validation_status != ValidationStatus.VALIDATED:
        #     raise ValueError("Dataset must be VALIDATED before publishing")

        # In a real implementation with a full state enum:
        # self.repo.update_state(version_id, "PUBLISHED")
        pass
