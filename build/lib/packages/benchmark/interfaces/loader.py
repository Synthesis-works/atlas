from abc import ABC, abstractmethod
from typing import Any

from ..models import Benchmark


class BaseLoader(ABC):
    """Abstract base class for benchmark loaders."""

    @abstractmethod
    def load(self, source: str) -> Benchmark:
        """Load a benchmark from the given source."""
        pass


class FileLoader(BaseLoader):
    """Abstract base class for file-based benchmark loaders."""

    @abstractmethod
    def load_file(self, file_path: str) -> dict[str, Any]:
        """Load raw dictionary from a file."""
        pass

    def load(self, source: str) -> Benchmark:
        """Load a benchmark from a file path."""
        data = self.load_file(source)
        return Benchmark(**data)
