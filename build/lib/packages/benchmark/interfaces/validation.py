from abc import ABC, abstractmethod

from ..models import Benchmark


class BaseValidator(ABC):
    """Abstract base class for validators."""

    @abstractmethod
    def validate(self, benchmark: Benchmark) -> bool:
        """Validate the benchmark. Raises exceptions on failure."""
        pass
