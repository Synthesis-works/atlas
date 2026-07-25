from abc import ABC, abstractmethod
from typing import Any


class BaseEvaluator(ABC):
    """
    Abstract interface for evaluation strategies.
    Each strategy should implement this interface to take a reference output and a predicted output,
    and return an EvaluationResult representation.
    """

    @abstractmethod
    def evaluate(self, reference: Any, prediction: Any) -> tuple[bool, float, dict[str, Any]]:
        """
        Evaluates a prediction against a reference.

        Args:
            reference: The ground truth / expected answer from the test case.
            prediction: The actual output from the model.

        Returns:
            Tuple containing:
            - passed (bool): Whether the test case passed.
            - score (float): A numeric score (usually between 0.0 and 1.0).
            - raw_measurements (dict): Any strategy-specific metadata or intermediate measurements.
        """
        pass
