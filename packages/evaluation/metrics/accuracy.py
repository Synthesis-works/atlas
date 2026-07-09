from typing import List, Any
from .base import BaseMetric
from ..results.result import EvaluationResult
from ..results.status import EvaluationStatus

class AccuracyMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "accuracy"
        
    def compute(self, results: List[EvaluationResult]) -> Any:
        if not results:
            return 0.0
        passed = sum(1 for r in results if r.status == EvaluationStatus.PASS)
        return (passed / len(results)) * 100.0
