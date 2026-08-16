from typing import Any

from packages.llm.prompt_builder import PromptBuilder
from packages.orchestrator.models import TaskRunResult, TaskRunState
from packages.orchestrator.pipeline.base import PipelineStage


class PromptStage(PipelineStage):
    def execute(self, context: dict[str, Any], result: TaskRunResult) -> None:
        if result.state == TaskRunState.FAILED:
            return

        task = context["task"]
        prompt_version = getattr(context.get("job_config"), "prompt_version", "v1")
        pack_name = context.get("pack_name")
        try:
            prompt = PromptBuilder.build_from_task(
                task,
                version=prompt_version,
                benchmark_pack=pack_name,  # type: ignore
            )
            context["prompt"] = prompt
            result.prompt = prompt.user
        except Exception as e:
            result.state = TaskRunState.FAILED
            result.error_message = f"Failed to build prompt: {str(e)}"
