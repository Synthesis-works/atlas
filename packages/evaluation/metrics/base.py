from abc import ABC, abstractmethod
from typing import List, Any
from ..results.result import EvaluationResult

class BaseMetric(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @abstractmethod
    def compute(self, results: List[EvaluationResult]) -> Any:
        """Compute metric from a list of evaluation results."""
        pass
