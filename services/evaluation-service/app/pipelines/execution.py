from typing import Any, Dict, List
from .base import EvaluationPipeline, PipelineContext, EvaluationResultBundle, MetricValueModel
from .registry import PipelineRegistry

class ExecutionPipeline(EvaluationPipeline):
    def evaluate(self, context: PipelineContext) -> EvaluationResultBundle:
        outputs = context.execution_outputs
        
        if not outputs:
            return EvaluationResultBundle()

        passed_count = 0
        total_count = len(outputs)

        for output in outputs:
            # Assuming execution output has a 'success' or 'status' field
            if output.get("success") is True or output.get("status") == "passed":
                passed_count += 1
                
        pass_rate = passed_count / total_count if total_count > 0 else 0.0

        metrics = [
            MetricValueModel(
                name="pass_rate",
                value=pass_rate,
                category="CORRECTNESS",
                direction="HIGHER_IS_BETTER",
                unit="percentage",
                source="ExecutionPipeline",
                aggregation="mean"
            ),
            MetricValueModel(
                name="pass_count",
                value=float(passed_count),
                category="CORRECTNESS",
                direction="HIGHER_IS_BETTER",
                unit="count",
                source="ExecutionPipeline",
                aggregation="sum"
            )
        ]

        # Calculate pass@k if requested in config
        if "k" in context.configuration:
            k = context.configuration["k"]
            # A simplistic pass@k implementation for demonstration purposes
            pass_at_k = 1.0 if passed_count >= k else 0.0
            metrics.append(
                MetricValueModel(
                    name=f"pass@{k}",
                    value=pass_at_k,
                    category="CORRECTNESS",
                    direction="HIGHER_IS_BETTER",
                    unit="binary",
                    source="ExecutionPipeline",
                    aggregation="mean"
                )
            )

        return EvaluationResultBundle(
            metrics=metrics,
            artifacts=[],
            judge_traces=[],
            warnings={},
            metadata={"total_executions": total_count}
        )

PipelineRegistry.register("ExecutionPipeline", ExecutionPipeline)
