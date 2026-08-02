from abc import ABC, abstractmethod


class BaseJudge(ABC):
    @abstractmethod
    def evaluate(self, expected: str, actual: str) -> tuple[bool, float, float]:
        """
        Evaluates actual against expected.
        Returns: (passed: bool, score: float, confidence: float)
        """
        pass
