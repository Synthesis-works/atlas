from typing import Dict, Any
from packages.orchestrator.pipeline.base import PipelineStage
from packages.orchestrator.models import TaskRunResult, TaskRunState

class EvaluationStage(PipelineStage):
    def execute(self, context: Dict[str, Any], result: TaskRunResult) -> None:
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
