from typing import Any

from ..results.result import EvaluationResult
from .base import BaseMetric


class LatencyMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "avg_latency_ms"

    def compute(self, results: list[EvaluationResult]) -> Any:
        if not results:
            return 0.0
        total_latency = sum(r.latency_ms for r in results)
        return total_latency / len(results)
