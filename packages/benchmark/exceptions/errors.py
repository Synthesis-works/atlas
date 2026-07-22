class BenchmarkError(Exception):
    """Base class for all benchmark exceptions."""

    pass


class BenchmarkValidationError(BenchmarkError):
    """Raised when a benchmark fails validation."""

    pass


class DuplicateBenchmarkError(BenchmarkError):
    """Raised when attempting to register a benchmark ID that already exists."""

    pass


class LoaderError(BenchmarkError):
    """Raised when failing to load a benchmark definition."""

    pass


class RegistryError(BenchmarkError):
    """Raised for errors within the registry operations."""

    pass


class ImporterError(BenchmarkError):
    """Raised when a dataset importer fails."""

    pass
