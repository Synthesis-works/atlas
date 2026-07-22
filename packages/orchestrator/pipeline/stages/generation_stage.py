import time
from typing import Any

from packages.orchestrator.models import TaskRunResult, TaskRunState
from packages.orchestrator.pipeline.base import PipelineStage


class GenerationStage(PipelineStage):
    def execute(self, context: dict[str, Any], result: TaskRunResult) -> None:
        if result.state == TaskRunState.FAILED:
            return

        adapter = context["provider_adapter"]
        prompt = context["prompt"]
        config = context["job_config"]

        try:
            start = time.time()
            response = adapter.generate(provider=config.provider, model=config.model, prompt=prompt)
            end = time.time()

            result.raw_response = response.response
            result.generation_latency_ms = int((end - start) * 1000)
            result.state = TaskRunState.GENERATED
        except Exception as e:
            result.state = TaskRunState.FAILED
            result.error_message = f"Failed to generate: {str(e)}"
