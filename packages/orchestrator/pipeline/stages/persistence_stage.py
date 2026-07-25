from typing import Any

from packages.orchestrator.models import TaskRunResult, TaskRunState
from packages.orchestrator.pipeline.base import PipelineStage


class PersistenceStage(PipelineStage):
    def execute(self, context: dict[str, Any], result: TaskRunResult) -> None:
        # Populate final metrics for serialization
        if result.prompt_tokens is not None and result.completion_tokens is not None:
            result.tokens = result.prompt_tokens + result.completion_tokens

        if result.evaluation_status:
            result.status = result.evaluation_status.upper()
        elif result.state == TaskRunState.FAILED:
            result.status = "ERROR"

        state_mgr = context["state_manager"]
        config = context["job_config"]
        state_mgr.save_task_result(config.job_id, result)
