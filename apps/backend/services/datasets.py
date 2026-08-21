import uuid
from collections.abc import Sequence

from atlas_db.models.dataset import Dataset, DatasetStatus
from atlas_db.repositories.dataset import DatasetRepository, DatasetVersionRepository
from sqlalchemy import select

from apps.backend.schemas.datasets import DatasetCreate


class DatasetService:
    def __init__(self, dataset_repo: DatasetRepository, version_repo: DatasetVersionRepository):
        self.dataset_repo = dataset_repo
        self.version_repo = version_repo

    def get_dataset(self, dataset_id: uuid.UUID) -> Dataset | None:
        dataset = self.dataset_repo.get(dataset_id)
        if dataset and dataset.status == DatasetStatus.ARCHIVED:
            return None
        return dataset

    def list_datasets(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Dataset]:
        stmt = (
            select(Dataset)
            .where(Dataset.project_id == project_id, Dataset.status != DatasetStatus.ARCHIVED)
            .offset(skip)
            .limit(limit)
        )
        return list(self.dataset_repo.db.execute(stmt).scalars().all())

    def create_dataset(
        self, project_id: uuid.UUID, member_id: uuid.UUID, data: DatasetCreate
    ) -> Dataset:
        dataset = Dataset(
            project_id=project_id,
            created_by_member_id=member_id,
            status=DatasetStatus.ACTIVE,
            **data.model_dump(),
        )
        return self.dataset_repo.create(dataset)
