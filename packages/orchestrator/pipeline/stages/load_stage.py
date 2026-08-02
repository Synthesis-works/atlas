from typing import Any

from packages.orchestrator.models import TaskRunResult, TaskRunState
from packages.orchestrator.pipeline.base import PipelineStage


class LoadTaskStage(PipelineStage):
    def execute(self, context: dict[str, Any], result: TaskRunResult) -> None:
        if result.state == TaskRunState.FAILED:
            return

        pack_tasks = context["pack_tasks"]

        try:
            task = pack_tasks.get(result.task_id)
            if not task:
                raise ValueError(f"Task {result.task_id} not found in pack.")
            context["task"] = task
        except Exception as e:
            result.state = TaskRunState.FAILED
            result.error_message = f"Failed to load task: {str(e)}"
