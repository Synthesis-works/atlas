from abc import ABC, abstractmethod


class BaseRepairAgent(ABC):
    """
    Modular interface for a Repair Agent.
    """

    @abstractmethod
    def generate_repair(
        self, task_id: str, original_prompt: str, failed_code: str, error_message: str, model: str
    ) -> str | None:
        """
        Takes the failing context and generates a fixed python function.
        Returns the new extracted source code, or None if failed.
        """
        pass
