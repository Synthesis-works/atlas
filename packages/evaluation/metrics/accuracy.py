from typing import Any

from ..results.result import EvaluationResult
from ..results.status import EvaluationStatus
from .base import BaseMetric


class AccuracyMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "accuracy"

    def compute(self, results: list[EvaluationResult]) -> Any:
        if not results:
            return 0.0
        passed = sum(1 for r in results if r.status == EvaluationStatus.PASS)
        return (passed / len(results)) * 100.0
