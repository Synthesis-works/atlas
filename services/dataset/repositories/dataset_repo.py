from uuid import UUID

from atlas_db.models.dataset import (
    Dataset,
    DatasetLicense,
    DatasetLifecycle,
    DatasetRegistry,
    DatasetSource,
    DatasetVersion,
)
from sqlalchemy import select, update
from sqlalchemy.orm import Session


class DatasetRepository:
    """
    Handles all database operations for Dataset entities.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_dataset(self, dataset_id: UUID) -> Dataset | None:
        return self.db.get(Dataset, dataset_id)

    def create_dataset(self, dataset: Dataset) -> Dataset:
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def get_version(self, version_id: UUID) -> DatasetVersion | None:
        return self.db.get(DatasetVersion, version_id)

    def create_version(self, version: DatasetVersion) -> DatasetVersion:
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def update_version_status(self, version_id: UUID, status: DatasetLifecycle) -> None:
        stmt = (
            update(DatasetVersion)
            .where(DatasetVersion.id == version_id)
            .values(validation_status=status)
        )
        self.db.execute(stmt)
        self.db.commit()

    def update_version_checksum(self, version_id: UUID, checksum: str) -> None:
        stmt = (
            update(DatasetVersion).where(DatasetVersion.id == version_id).values(checksum=checksum)
        )
        self.db.execute(stmt)
        self.db.commit()


class RegistryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_registries(self) -> list[DatasetRegistry]:
        stmt = select(DatasetRegistry)
        return list(self.db.scalars(stmt))


class SourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_sources(self) -> list[DatasetSource]:
        stmt = select(DatasetSource)
        return list(self.db.scalars(stmt))


class LicenseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_licenses(self) -> list[DatasetLicense]:
        stmt = select(DatasetLicense)
        return list(self.db.scalars(stmt))
