import re

from .base import EvaluationPipeline, EvaluationResultBundle, MetricValueModel, PipelineContext
from .registry import PipelineRegistry


class RulePipeline(EvaluationPipeline):
    def evaluate(self, context: PipelineContext) -> EvaluationResultBundle:
        outputs = context.execution_outputs
        config = context.configuration

        pattern = config.get("regex_pattern")
        if not pattern:
            raise ValueError("RulePipeline requires 'regex_pattern' in configuration.")

        compiled_regex = re.compile(pattern)

        passed_count = 0
        total_count = len(outputs)

        for output in outputs:
            text = output.get("text", "")
            if compiled_regex.search(text):
                passed_count += 1

        pass_rate = passed_count / total_count if total_count > 0 else 0.0

        metrics = [
            MetricValueModel(
                name="regex_match_rate",
                value=pass_rate,
                category="CORRECTNESS",
                direction="HIGHER_IS_BETTER",
                unit="percentage",
                source="RulePipeline",
                aggregation="mean",
            )
        ]

        return EvaluationResultBundle(
            metrics=metrics,
            artifacts=[],
            judge_traces=[],
            warnings={},
            metadata={"pattern": pattern, "matched_count": passed_count},
        )


PipelineRegistry.register("RulePipeline", RulePipeline)
