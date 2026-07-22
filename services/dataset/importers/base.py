import abc

from ..storage.provider import StorageProvider


class DatasetImporter(abc.ABC):
    def __init__(self, storage: StorageProvider):
        self.storage = storage

    @abc.abstractmethod
    def import_file(self, file_obj, destination_path: str) -> str:
        """Imports the file and returns the stored path/URI."""
        pass


class CSVImporter(DatasetImporter):
    def import_file(self, file_obj, destination_path: str) -> str:
        # Potentially do lightweight checks here (like checking if it looks like a CSV)
        # But mostly just delegate to storage
        return self.storage.save(file_obj, destination_path)


class JSONImporter(DatasetImporter):
    def import_file(self, file_obj, destination_path: str) -> str:
        return self.storage.save(file_obj, destination_path)
