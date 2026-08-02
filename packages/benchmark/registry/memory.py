from typing import Any

from ..exceptions import DuplicateBenchmarkError
from ..interfaces.registry import BaseRegistry
from ..models import Benchmark


class InMemoryRegistry(BaseRegistry):
    """In-memory implementation of the benchmark registry."""

    def __init__(self):
        self._store: dict[str, Benchmark] = {}

    def register(self, benchmark: Benchmark) -> None:
        if benchmark.metadata.benchmark_id in self._store:
            raise DuplicateBenchmarkError(
                f"Benchmark with ID {benchmark.metadata.benchmark_id} already exists."
            )
        self._store[benchmark.metadata.benchmark_id] = benchmark

    def get(self, benchmark_id: str) -> Benchmark | None:
        return self._store.get(benchmark_id)

    def list_benchmarks(self, filters: dict[str, Any] | None = None) -> list[Benchmark]:
        benchmarks = list(self._store.values())
        if not filters:
            return benchmarks

        filtered = []
        for b in benchmarks:
            match = True
            for k, v in filters.items():
                if getattr(b.metadata, k, None) != v:
                    match = False
                    break
            if match:
                filtered.append(b)
        return filtered

    def remove(self, benchmark_id: str) -> bool:
        if benchmark_id in self._store:
            del self._store[benchmark_id]
            return True
        return False
