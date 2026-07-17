from abc import ABC, abstractmethod
from typing import Optional

class BaseRepairAgent(ABC):
    """
    Modular interface for a Repair Agent.
    """
    @abstractmethod
    def generate_repair(self, task_id: str, original_prompt: str, failed_code: str, error_message: str, model: str) -> Optional[str]:
        """
        Takes the failing context and generates a fixed python function.
        Returns the new extracted source code, or None if failed.
        """
        pass
