import subprocess
import time
from typing import Tuple
from ..exceptions import ExecutionTimeoutException

class ProcessMonitor:
    @staticmethod
    def run_with_timeout(cmd: list[str], cwd: str, timeout: int) -> Tuple[int, str, str, int]:
        """
        Executes a command with a strict timeout.
        Returns (exit_code, stdout, stderr, runtime_ms).
        Raises ExecutionTimeoutException if it times out.
        """
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            runtime_ms = int((time.time() - start_time) * 1000)
            return result.returncode, result.stdout, result.stderr, runtime_ms
        except subprocess.TimeoutExpired as e:
            runtime_ms = int((time.time() - start_time) * 1000)
            stdout = e.stdout.decode('utf-8') if e.stdout else ""
            stderr = e.stderr.decode('utf-8') if e.stderr else f"Execution timed out after {timeout} seconds."
            raise ExecutionTimeoutException(stderr)
        except Exception as e:
            raise e
