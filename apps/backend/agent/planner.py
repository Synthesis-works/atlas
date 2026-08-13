import logging
from typing import Any, Dict, List, Optional

from apps.backend.agent.state import AgentDecision, AgentTask, PlanStep

logger = logging.getLogger(__name__)


class AgentPlanner:
    """
    Manages task planning, step tracking, re-planning, and failure repair strategy formulation.
    """

    def generate_initial_plan(self, goal: str) -> list[PlanStep]:
        """
        Creates an initial structured plan based on the goal description.
        """
        return [
            PlanStep(step_number=1, description="Define benchmark specification", status="PENDING"),
            PlanStep(step_number=2, description="Generate and attach dataset tasks", status="PENDING"),
            PlanStep(step_number=3, description="Generate evaluation cases and ground truth", status="PENDING"),
            PlanStep(step_number=4, description="Validate task formats and completeness", status="PENDING"),
            PlanStep(step_number=5, description="Run target model executions", status="PENDING"),
            PlanStep(step_number=6, description="Evaluate outputs using evaluation cases", status="PENDING"),
            PlanStep(step_number=7, description="Publish comparative benchmark report", status="PENDING"),
        ]

    def update_plan_on_decision(self, task: AgentTask, decision: AgentDecision, observation: Optional[dict[str, Any]]) -> None:
        """
        Updates task plan step statuses based on executed tool decisions and observations.
        """
        if not task.plan:
            task.plan = self.generate_initial_plan(task.goal)

        if decision.tool_name in {"create_benchmark", "search_benchmarks"}:
            self._set_step_status(task.plan, 1, "COMPLETED", "Benchmark defined.")
        elif decision.tool_name in {"create_dataset", "get_dataset"}:
            self._set_step_status(task.plan, 2, "COMPLETED", "Dataset created.")
        elif decision.tool_name == "create_evaluation_case":
            self._set_step_status(task.plan, 3, "COMPLETED", "Evaluation cases generated.")
        elif decision.tool_name == "validate_benchmark_dataset":
            if observation and isinstance(observation, dict) and not observation.get("valid", True):
                self._set_step_status(task.plan, 4, "FAILED", f"Validation failed ({observation.get('invalid_count', 0)} invalid tasks).")
            else:
                self._set_step_status(task.plan, 4, "COMPLETED", "Dataset validation passed.")
        elif decision.tool_name == "update_dataset":
            self._set_step_status(task.plan, 4, "REPAIRED", "Dataset tasks repaired. Re-validation required.")
        elif decision.tool_name in {"run_benchmark", "get_run_status"}:
            self._set_step_status(task.plan, 5, "COMPLETED", "Executions finished.")
        elif decision.tool_name in {"evaluate_run", "compare_results"}:
            self._set_step_status(task.plan, 6, "COMPLETED", "Evaluation completed.")
        elif decision.tool_name == "generate_report":
            self._set_step_status(task.plan, 7, "COMPLETED", "Report generated.")

    def _set_step_status(self, plan: list[PlanStep], step_number: int, status: str, summary: str) -> None:
        for p in plan:
            if p.step_number == step_number:
                p.status = status
                p.result_summary = summary
                break
