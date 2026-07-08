from typing import List, Any
from .base import BaseMetric
from ..results.result import EvaluationResult

class LatencyMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "avg_latency_ms"
        
    def compute(self, results: List[EvaluationResult]) -> Any:
        if not results:
            return 0.0
        total_latency = sum(r.latency_ms for r in results)
        return total_latency / len(results)
