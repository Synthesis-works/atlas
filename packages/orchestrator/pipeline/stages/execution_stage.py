from typing import Any

from packages.orchestrator.models import TaskRunResult, TaskRunState
from packages.orchestrator.pipeline.base import PipelineStage
from packages.runtime.models.execution_request import ExecutionContext, ExecutionRequest


class ExecutionStage(PipelineStage):
    def execute(self, context: dict[str, Any], result: TaskRunResult) -> None:
        if result.state == TaskRunState.FAILED:
            return

        task = context["task"]
        config = context["job_config"]
        runtime_mgr = context["runtime_manager"]

        tests_str = ""
        setup_code = task.metadata.get("test_setup_code")
        if setup_code:
            tests_str += f"{setup_code}\n\n"
        if isinstance(task.hidden_tests, list):
            for ht in task.hidden_tests:
                if isinstance(ht, dict):
                    tests_str += f"assert {ht.get('input')} == {ht.get('expected_output')}\n"
                else:
                    tests_str += f"{ht}\n"
        elif isinstance(task.hidden_tests, str):
            tests_str = task.hidden_tests

        req = ExecutionRequest(  # type: ignore
            code=result.extracted_code or "UNKNOWN",
            hidden_tests=tests_str,
            context=ExecutionContext(language="python", timeout=5, memory_limit=256),  # type: ignore
        )

        try:
            exec_res = runtime_mgr.execute(req, task_id=task.task_id, model_id=config.model)
            result.execution_status = exec_res.status.value
            result.tests_passed = exec_res.passed
            result.execution_latency_ms = exec_res.runtime_ms
            result.stdout = exec_res.stdout
            result.stderr = exec_res.stderr
            result.exception = exec_res.exception
            result.state = TaskRunState.EXECUTED
        except Exception as e:
            result.state = TaskRunState.FAILED
            result.error_message = f"Failed to execute runtime: {str(e)}"
