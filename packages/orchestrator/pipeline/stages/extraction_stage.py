from typing import Dict, Any
from packages.orchestrator.pipeline.base import PipelineStage
from packages.orchestrator.models import TaskRunResult, TaskRunState
from packages.evaluation.extractors.code_block import CodeBlockExtractor

class ExtractionStage(PipelineStage):
    def execute(self, context: Dict[str, Any], result: TaskRunResult) -> None:
        if result.state == TaskRunState.FAILED:
            return
            
        extractor = CodeBlockExtractor()
        try:
            code = extractor.extract(result.raw_response)
            result.extracted_code = code
        except Exception as e:
            result.state = TaskRunState.FAILED
            result.error_message = f"Failed to extract: {str(e)}"
