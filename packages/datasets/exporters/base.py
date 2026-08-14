import abc
from dataclasses import dataclass
from packages.datasets.models import TrainingExample

@dataclass
class DatasetExportResult:
    content: bytes
    mime_type: str
    filename_extension: str

class DatasetExporter(abc.ABC):
    @abc.abstractmethod
    def export(self, examples: list[TrainingExample]) -> DatasetExportResult:
        """
        Produce a deterministic serialized artifact representing the dataset payload.
        """
        pass
