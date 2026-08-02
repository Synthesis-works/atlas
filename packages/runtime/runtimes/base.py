from abc import ABC, abstractmethod

from ..models.execution_request import ExecutionRequest
from ..models.execution_result import ExecutionResult


class BaseRuntime(ABC):
    """Base interface for all language runtimes."""

    @abstractmethod
    def supports_language(self, language: str) -> bool:
        """Returns True if this runtime supports the given language."""
        pass

    @abstractmethod
    def validate(self, request: ExecutionRequest) -> None:
        """Validates the execution request (e.g. security checks). Raises exceptions if invalid."""
        pass

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Executes the request and returns the result."""
        pass
