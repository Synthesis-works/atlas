from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class ExportResult:
    content: bytes
    mime_type: str
    filename_extension: str


class Exporter(ABC):
    @abstractmethod
    def export(self, data: Iterable[Any]) -> ExportResult:
        """Export the provided iterable of data (usually DTOs or dicts) into a byte format."""
        pass
