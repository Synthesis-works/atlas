from typing import Any

from ..interfaces.loader import BaseLoader
from ..interfaces.registry import BaseRegistry
from ..interfaces.validation import BaseValidator
from ..models import Benchmark


class BenchmarkManager:
    """Facade for managing benchmarks, orchestrating loaders, validators, and registries."""

    def __init__(
        self,
        registry: BaseRegistry,
        validators: list[BaseValidator],
        loaders: dict[str, BaseLoader],
    ):
        self.registry = registry
        self.validators = validators
        self.loaders = loaders

    def load_and_register(self, source: str, format: str) -> Benchmark:
        """Load a benchmark from a source, validate it, and register it."""
        if format not in self.loaders:
            raise ValueError(f"No loader configured for format '{format}'")

        loader = self.loaders[format]
        benchmark = loader.load(source)

        # Validate
        for validator in self.validators:
            validator.validate(benchmark)

        # Register
        self.registry.register(benchmark)

        return benchmark

    def get_benchmark(self, benchmark_id: str) -> Benchmark | None:
        """Retrieve a benchmark from the registry."""
        return self.registry.get(benchmark_id)

    def search_benchmarks(self, filters: dict[str, Any] | None = None) -> list[Benchmark]:
        """Search benchmarks in the registry."""
        return self.registry.list_benchmarks(filters)

    def remove_benchmark(self, benchmark_id: str) -> bool:
        """Remove a benchmark from the registry."""
        return self.registry.remove(benchmark_id)
