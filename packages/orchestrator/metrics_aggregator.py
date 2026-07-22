from typing import Any

from .models import TaskRunResult


class MetricsAggregator:
    @staticmethod
    def aggregate(results: list[TaskRunResult]) -> dict[str, Any]:
        total_tasks = len(results)
        if total_tasks == 0:
            return {}

        passed = 0
        total_latency = 0
        total_exec_time = 0

        syntax_errors = 0
        runtime_errors = 0
        timeouts = 0
        security_violations = 0
        extraction_failures = 0
        logic_errors = 0
        model_refusals = 0

        prompt_compliance = 0

        repairable_errors = 0
        unrepairable_errors = 0

        for r in results:
            if r.evaluation_status == "pass":
                passed += 1
            elif r.evaluation_status == "fail":
                # Executed without exception, but failed tests
                if r.execution_status == "success":
                    logic_errors += 1
                    unrepairable_errors += 1
                elif r.execution_status in ["runtime_error", "syntax_error"]:
                    if r.stderr and any(
                        e in r.stderr for e in ["NameError", "ImportError", "ModuleNotFoundError"]
                    ):
                        repairable_errors += 1
                    else:
                        unrepairable_errors += 1
                elif r.execution_status in ["timeout", "security_violation"]:
                    unrepairable_errors += 1

            if r.generation_latency_ms:
                total_latency += r.generation_latency_ms

            if r.execution_latency_ms:
                total_exec_time += r.execution_latency_ms

            if r.execution_status == "syntax_error":
                syntax_errors += 1
            elif r.execution_status == "runtime_error":
                runtime_errors += 1
            elif r.execution_status == "timeout":
                timeouts += 1
            elif r.execution_status == "security_violation":
                security_violations += 1

            if not r.extracted_code or r.extracted_code.strip() == "UNKNOWN":
                extraction_failures += 1
                if r.raw_response and any(
                    refusal in r.raw_response.lower()
                    for refusal in [
                        "i cannot",
                        "i apologize",
                        "as an ai",
                        "not enough information",
                        "i'm sorry",
                    ]
                ):
                    model_refusals += 1
            else:
                prompt_compliance += 1

        return {
            "total_tasks": total_tasks,
            "pass_at_1": passed / total_tasks,
            "average_latency_ms": (total_latency / total_tasks) if total_tasks else 0,
            "average_execution_ms": (total_exec_time / total_tasks) if total_tasks else 0,
            "syntax_error_rate": syntax_errors / total_tasks,
            "runtime_error_rate": runtime_errors / total_tasks,
            "logic_error_rate": logic_errors / total_tasks,
            "timeout_rate": timeouts / total_tasks,
            "security_violation_rate": security_violations / total_tasks,
            "extraction_failure_rate": extraction_failures / total_tasks,
            "model_refusal_rate": model_refusals / total_tasks,
            "prompt_compliance_rate": prompt_compliance / total_tasks,
            "repairable_error_rate": repairable_errors / total_tasks,
            "unrepairable_error_rate": unrepairable_errors / total_tasks,
        }
