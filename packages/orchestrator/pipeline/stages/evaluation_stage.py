from typing import Any

from packages.orchestrator.models import TaskRunResult, TaskRunState
from packages.orchestrator.pipeline.base import PipelineStage


class EvaluationStage(PipelineStage):
    def execute(self, context: dict[str, Any], result: TaskRunResult) -> None:
        if result.state == TaskRunState.FAILED:
            return

        try:
            if result.tests_passed:
                result.evaluation_status = "pass"
                result.score = 1.0
                result.confidence = 1.0
            else:
                result.evaluation_status = "fail"
                result.score = 0.0
                result.confidence = 1.0

            result.state = TaskRunState.EVALUATED
        except Exception as e:
            result.state = TaskRunState.FAILED
            result.error_message = f"Failed to evaluate: {str(e)}"
