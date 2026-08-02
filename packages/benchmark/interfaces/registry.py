from abc import ABC, abstractmethod
from typing import Any

from ..models import Benchmark


class BaseRegistry(ABC):
    """Abstract base class for a benchmark registry."""

    @abstractmethod
    def register(self, benchmark: Benchmark) -> None:
        """Register a new benchmark."""
        pass

    @abstractmethod
    def get(self, benchmark_id: str) -> Benchmark | None:
        """Retrieve a benchmark by ID."""
        pass

    @abstractmethod
    def list_benchmarks(self, filters: dict[str, Any] | None = None) -> list[Benchmark]:
        """List all benchmarks, optionally applying filters."""
        pass

    @abstractmethod
    def remove(self, benchmark_id: str) -> bool:
        """Remove a benchmark from the registry."""
        pass
