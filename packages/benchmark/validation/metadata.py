import re

from ..exceptions import BenchmarkValidationError
from ..interfaces.validation import BaseValidator
from ..models import Benchmark


class MetadataValidator(BaseValidator):
    """Validates metadata fields that require business logic beyond schema types."""

    def validate(self, benchmark: Benchmark) -> bool:
        metadata = benchmark.metadata

        # Check semantic versioning format
        semver_regex = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        if not re.match(semver_regex, metadata.version):
            raise BenchmarkValidationError(
                f"Invalid version format '{metadata.version}'. Must be semantic versioning."
            )

        if not metadata.benchmark_id.strip():
            raise BenchmarkValidationError("Benchmark ID cannot be empty.")

        return True
