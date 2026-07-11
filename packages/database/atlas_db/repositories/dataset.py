from sqlalchemy.orm import Session
from .base import BaseRepository
from atlas_db.models.dataset import Dataset, DatasetVersion, DatasetRegistry, DatasetSource, DatasetLicense

class DatasetRepository(BaseRepository[Dataset]):
    model = Dataset

class DatasetVersionRepository(BaseRepository[DatasetVersion]):
    model = DatasetVersion

class DatasetRegistryRepository(BaseRepository[DatasetRegistry]):
    model = DatasetRegistry

class DatasetSourceRepository(BaseRepository[DatasetSource]):
    model = DatasetSource

class DatasetLicenseRepository(BaseRepository[DatasetLicense]):
    model = DatasetLicense
