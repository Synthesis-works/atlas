from typing import Any, Dict
from .base import EvaluationPipeline, PipelineContext, EvaluationResultBundle, MetricValueModel, JudgeTraceModel
from .registry import PipelineRegistry
from app.judges.base import JudgeProvider

class JudgePipeline(EvaluationPipeline):
    def __init__(self, provider: JudgeProvider):
        self.provider = provider

    def evaluate(self, context: PipelineContext) -> EvaluationResultBundle:
        outputs = context.execution_outputs
        config = context.configuration

        rubric = config.get("rubric", "Default Rubric")
        prompt_template = config.get("prompt_template", "Evaluate this output: {output}")

        traces = []
        metrics = []

        if not outputs:
            return EvaluationResultBundle()

        total_score = 0.0

        for output in outputs:
            text = output.get("text", "")
            prompt = prompt_template.format(output=text)
            
            response = self.provider.evaluate(prompt=prompt, rubric=rubric)
            
            trace = JudgeTraceModel(
                prompt=prompt,
                response=response.reasoning,
                rubric=rubric,
                reasoning=response.reasoning,
                latency_ms=response.metadata.get("latency_ms") if response.metadata else None,
                cost=response.metadata.get("cost") if response.metadata else None,
                metadata=response.metadata
            )
            traces.append(trace)
            total_score += response.score

        avg_score = total_score / len(outputs) if outputs else 0.0

        metrics.append(
            MetricValueModel(
                name="judge_score",
                value=avg_score,
                category="QUALITY",
                direction="HIGHER_IS_BETTER",
                unit="score",
                source="JudgePipeline",
                aggregation="mean"
            )
        )

        return EvaluationResultBundle(
            metrics=metrics,
            artifacts=[],
            judge_traces=traces,
            warnings={},
            metadata={"evaluated_count": len(outputs)}
        )

# Cannot automatically register without knowing the provider, 
# but we can register a factory or depend on dependency injection for real pipelines.
