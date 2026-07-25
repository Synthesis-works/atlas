from abc import ABC, abstractmethod
from typing import Any

from packages.orchestrator.models import TaskRunResult


class PipelineStage(ABC):
    """Base class for all pipeline stages."""

    @abstractmethod
    def execute(self, context: dict[str, Any], result: TaskRunResult) -> None:
        """
        Executes the stage.

        Args:
            context: Shared dictionary for passing data between stages.
            result: The TaskRunResult object to mutate.
        """
        pass
