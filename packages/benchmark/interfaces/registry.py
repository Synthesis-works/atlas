from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..models import Benchmark

class BaseRegistry(ABC):
    """Abstract base class for a benchmark registry."""

    @abstractmethod
    def register(self, benchmark: Benchmark) -> None:
        """Register a new benchmark."""
        pass

    @abstractmethod
    def get(self, benchmark_id: str) -> Optional[Benchmark]:
        """Retrieve a benchmark by ID."""
        pass

    @abstractmethod
    def list_benchmarks(self, filters: Optional[Dict[str, Any]] = None) -> List[Benchmark]:
        """List all benchmarks, optionally applying filters."""
        pass

    @abstractmethod
    def remove(self, benchmark_id: str) -> bool:
        """Remove a benchmark from the registry."""
        pass
