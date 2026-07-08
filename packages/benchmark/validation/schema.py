from ..interfaces.validation import BaseValidator
from ..models import Benchmark
from ..exceptions import BenchmarkValidationError
from pydantic import ValidationError

class SchemaValidator(BaseValidator):
    """Validates the structure and types of the benchmark using Pydantic."""
    
    def validate(self, benchmark: Benchmark) -> bool:
        try:
            # Re-validate to ensure deep integrity
            Benchmark.model_validate(benchmark.model_dump())
            return True
        except ValidationError as e:
            raise BenchmarkValidationError(f"Schema validation failed: {e}")
