from abc import ABC, abstractmethod
from typing import Tuple

class BaseJudge(ABC):
    @abstractmethod
    def evaluate(self, expected: str, actual: str) -> Tuple[bool, float, float]:
        """
        Evaluates actual against expected.
        Returns: (passed: bool, score: float, confidence: float)
        """
        pass
