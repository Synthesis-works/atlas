import uuid
from typing import List, Dict, Any
from .pipeline import EvaluationPipeline
from .results.result import EvaluationResult
from .metrics.accuracy import AccuracyMetric
from .metrics.latency import LatencyMetric

class EvaluationManager:
    def __init__(self):
        self.pipeline = EvaluationPipeline()
        self.metrics = [AccuracyMetric(), LatencyMetric()]

    def run_evaluation(self, benchmark_id: str, task, llm_response) -> EvaluationResult:
        status, normalized, score, confidence = self.pipeline.evaluate(
            config=task.evaluation,
            expected=task.expected_output,
            actual=llm_response.response
        )
        
        return EvaluationResult(
            id=str(uuid.uuid4()),
            benchmark_id=benchmark_id,
            task_id=task.task_id,
            provider=llm_response.provider,
            model=llm_response.model,
            judge=task.evaluation.judge,
            status=status,
            expected=str(task.expected_output),
            actual=llm_response.response,
            normalized_output=normalized,
            latency_ms=llm_response.latency_ms,
            score=score,
            confidence=confidence
        )
        
    def compute_metrics(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        report = {}
        for metric in self.metrics:
            report[metric.name] = metric.compute(results)
        return report
