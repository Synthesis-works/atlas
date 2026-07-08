from ..interfaces.validation import BaseValidator
from ..models import Benchmark
from ..interfaces.registry import BaseRegistry
from ..exceptions import BenchmarkValidationError

class RegistryValidator(BaseValidator):
    """Validates benchmark against the registry (e.g., uniqueness)."""
    
    def __init__(self, registry: BaseRegistry):
        self.registry = registry

    def validate(self, benchmark: Benchmark) -> bool:
        existing = self.registry.get(benchmark.metadata.benchmark_id)
        if existing is not None:
            raise BenchmarkValidationError(
                f"Benchmark ID '{benchmark.metadata.benchmark_id}' is already registered."
            )
        return True
