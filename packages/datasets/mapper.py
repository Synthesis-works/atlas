from abc import ABC, abstractmethod
from typing import Any
from packages.benchmark.models.task import Task

class BaseMapper(ABC):
    @abstractmethod
    def map(self, raw_record: Any) -> Task:
        """Converts a raw dataset record into an Atlas Task schema."""
        pass
