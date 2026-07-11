from typing import Dict, Any
from packages.orchestrator.pipeline.base import PipelineStage
from packages.orchestrator.models import TaskRunResult, TaskRunState

class LoadTaskStage(PipelineStage):
    def execute(self, context: Dict[str, Any], result: TaskRunResult) -> None:
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
