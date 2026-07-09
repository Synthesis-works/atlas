from typing import Dict, Optional
from ..models.execution_request import ExecutionRequest
from ..models.execution_result import ExecutionResult
from ..runtimes.base import BaseRuntime
from ..runtimes.python_runtime import PythonRuntime
from ..utils.logger import RuntimeLogger
from ..exceptions import SandboxException

class RuntimeManager:
    def __init__(self, logs_dir: str = "logs"):
        self.logger = RuntimeLogger(logs_dir=logs_dir)
        self.runtimes: Dict[str, BaseRuntime] = {
            "python": PythonRuntime(),
            "python3": PythonRuntime()
        }

    def register_runtime(self, language: str, runtime: BaseRuntime):
        self.runtimes[language.lower()] = runtime

    def execute(self, request: ExecutionRequest, task_id: str = "unknown", model_id: str = "unknown") -> ExecutionResult:
        lang = request.context.language.lower()
        if lang not in self.runtimes:
            raise SandboxException(f"No runtime registered for language: {lang}")
            
        runtime = self.runtimes[lang]
        result = runtime.execute(request)
        
        self.logger.log_execution(task_id=task_id, model_id=model_id, result=result)
        
        return result
