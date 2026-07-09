from abc import ABC, abstractmethod
from typing import Any
from ..models import Benchmark

class BaseImporter(ABC):
    """Abstract base class for dataset importers."""
    
    @abstractmethod
    def import_data(self, source: Any, **kwargs) -> Benchmark:
        """Import dataset and convert to a Benchmark object."""
        pass
