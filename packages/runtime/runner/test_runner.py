import os


class TestRunnerGenerator:
    """Generates the runner script for execution."""

    @staticmethod
    def generate_python_runner(sandbox_dir: str, code: str, hidden_tests: str) -> str:
        """
        Writes solution.py and runner.py in the sandbox.
        Returns the absolute path to runner.py.
        """
        solution_path = os.path.join(sandbox_dir, "solution.py")
        runner_path = os.path.join(sandbox_dir, "runner.py")

        with open(solution_path, "w", encoding="utf-8") as f:
            f.write(code)

        runner_code = [
            "import sys",
            "from solution import *",
            "",
            "# --- Hidden Tests ---",
            hidden_tests if hidden_tests else "pass",
            "",
            "print('__ATLAS_SUCCESS__')",
        ]

        with open(runner_path, "w", encoding="utf-8") as f:
            f.write("\n".join(runner_code))

        return runner_path
