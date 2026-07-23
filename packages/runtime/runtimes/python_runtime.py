import sys
import uuid

from ..exceptions import CompilationException, ExecutionTimeoutException, SecurityException
from ..models.execution_request import ExecutionRequest
from ..models.execution_result import ExecutionResult, ExecutionStatus
from ..monitor.process import ProcessMonitor
from ..runner.test_runner import TestRunnerGenerator
from ..sandbox.tempdir import TemporarySandbox
from ..security.validator import SecurityValidator
from .base import BaseRuntime


class PythonRuntime(BaseRuntime):
    def __init__(self):
        self.validator = SecurityValidator()
        self.python_exe = sys.executable

    def supports_language(self, language: str) -> bool:
        return language.lower() in ("python", "python3")

    def validate(self, request: ExecutionRequest) -> None:
        self.validator.validate(request.code)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        run_id = str(uuid.uuid4())

        try:
            self.validate(request)
        except CompilationException as e:
            return ExecutionResult(  # type: ignore
                execution_id=run_id, status=ExecutionStatus.SYNTAX_ERROR, exception=str(e)
            )
        except SecurityException as e:
            return ExecutionResult(  # type: ignore
                execution_id=run_id, status=ExecutionStatus.SECURITY_VIOLATION, exception=str(e)
            )

        with TemporarySandbox(base_dir=request.context.working_directory) as sandbox_dir:
            runner_path = TestRunnerGenerator.generate_python_runner(
                sandbox_dir=sandbox_dir, code=request.code, hidden_tests=request.hidden_tests or ""
            )

            try:
                exit_code, stdout, stderr, runtime_ms = ProcessMonitor.run_with_timeout(
                    cmd=[self.python_exe, runner_path],
                    cwd=sandbox_dir,
                    timeout=request.context.timeout,
                )

                passed = exit_code == 0 and "__ATLAS_SUCCESS__" in stdout
                status = ExecutionStatus.SUCCESS if passed else ExecutionStatus.FAILURE

                if exit_code != 0 and "ImportError" in stderr:
                    status = ExecutionStatus.IMPORT_ERROR
                elif exit_code != 0 and "AssertionError" in stderr:
                    status = ExecutionStatus.SUCCESS  # Execution succeeded but logic failed
                elif exit_code != 0:
                    status = ExecutionStatus.RUNTIME_ERROR

                return ExecutionResult(  # type: ignore
                    execution_id=run_id,
                    status=status,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    runtime_ms=runtime_ms,
                    passed=passed,
                    failed=not passed,
                )

            except ExecutionTimeoutException as e:
                return ExecutionResult(  # type: ignore
                    execution_id=run_id,
                    status=ExecutionStatus.TIMEOUT,
                    stderr=str(e),
                    timed_out=True,
                    failed=True,
                )
            except Exception as e:
                return ExecutionResult(  # type: ignore
                    execution_id=run_id,
                    status=ExecutionStatus.UNKNOWN,
                    exception=str(e),
                    failed=True,
                )
