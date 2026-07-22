import abc
import os
import shutil


class StorageProvider(abc.ABC):
    @abc.abstractmethod
    def save(self, file_obj, destination_path: str) -> str:
        pass

    @abc.abstractmethod
    def get(self, path: str):
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "/tmp/atlas_datasets"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, file_obj, destination_path: str) -> str:
        full_path = os.path.join(self.base_dir, destination_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)
        return full_path

    def get(self, path: str):
        full_path = os.path.join(self.base_dir, path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Dataset file not found at {full_path}")
        return open(full_path, "rb")


# Future implementations:
# class S3StorageProvider(StorageProvider): ...
# class GCSStorageProvider(StorageProvider): ...
