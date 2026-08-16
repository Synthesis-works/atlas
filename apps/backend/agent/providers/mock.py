import logging
from typing import Any, Dict, List

from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask

logger = logging.getLogger(__name__)


class MockAgentProvider(BaseLLMProvider):
    """
    Deterministic rule-based provider for offline development and fast unit/integration testing.
    Drives a complete benchmark lifecycle step by step.
    """

    def decide(
        self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]
    ) -> AgentDecision:
        # Mock clarification trigger
        has_active_clarification = (
            task.status == "WAITING_FOR_CLARIFICATION" or task.clarification_id is not None
        )
        has_answered_clarification = (
            task.clarification_answer is not None or len(task.past_clarifications) > 0
        )
        if (
            task.run_mode != "RERUN"
            and "clarif" in task.goal.lower()
            and not has_active_clarification
            and not has_answered_clarification
        ):
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="request_clarification",
                arguments={"question": "Should we test addition or subtraction?"},
                reasoning="Goal is ambiguous. Ask for clarification.",
            )

        # Dynamic Plan-Driven Tool Selection
        plan = task.plan or []
        next_step = None
        for step in plan:
            if step.status in ["PENDING", "FAILED"]:
                next_step = step
                break

        if not next_step:
            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response=(
                    "Benchmark workflow completed successfully!\n"
                    "- Configuration setup resolved\n"
                    "- Dispatched executions for target models\n"
                    "- Evaluation completed & report generated."
                ),
                reasoning="All steps completed.",
            )

        desc = next_step.description.lower()

        # Step 1: Define benchmark specification
        if "define benchmark" in desc:
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="create_benchmark",
                arguments={
                    "name": "Python Vulnerability Detection Benchmark",
                    "description": "Evaluate LLMs on Python security flaw detection.",
                    "task_type": "security_code_audit",
                    "evaluation_method": "exact_match",
                },
                reasoning="Step 1: Create benchmark definition.",
            )

        # Step 2: Generate and attach dataset tasks
        if "generate and attach dataset" in desc:
            bm_id = task.benchmark_id or "00000000-0000-0000-0000-000000000001"
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="create_dataset",
                arguments={
                    "benchmark_id": bm_id,
                    "name": "Python SecVulnerability Samples v1",
                    "tasks": [
                        {
                            "id": "t1",
                            "input": "def eval_input(x): exec(x)",
                            "expected_output": "INSECURE_EVAL",
                        },
                        {
                            "id": "t2",
                            "input": "def query_db(q): db.execute(q)",
                            "expected_output": "SQL_INJECTION",
                        },
                        {
                            "id": "t3",
                            "input": "def bad_format(): pass",
                        },  # Missing expected_output for validation failure simulation
                    ],
                },
                reasoning="Step 2: Attach dataset tasks.",
            )

        # Step 3: Generate evaluation cases and ground truth
        if "generate evaluation cases" in desc:
            ds_id = task.dataset_id or "00000000-0000-0000-0000-000000000002"
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="create_evaluation_case",
                arguments={
                    "dataset_id": ds_id,
                    "evaluation_cases": [
                        {
                            "task_id": "t1",
                            "evaluation_method": "exact_match",
                            "expected_answer": "INSECURE_EVAL",
                        },
                        {
                            "task_id": "t2",
                            "evaluation_method": "exact_match",
                            "expected_answer": "SQL_INJECTION",
                        },
                    ],
                },
                reasoning="Step 3: Generate evaluation cases and ground truth.",
            )

        # Step 4: Validate task formats and completeness
        if "validate task formats" in desc:
            ds_id = task.dataset_id or "00000000-0000-0000-0000-000000000002"
            # If we validated once and update is pending, mock the repair call first
            called_tools = [c.tool_name for c in task.tool_calls]
            if (
                called_tools.count("validate_benchmark_dataset") == 1
                and "update_dataset" not in called_tools
            ):
                return AgentDecision(
                    type=AgentDecisionType.TOOL_CALL,
                    tool_name="update_dataset",
                    arguments={
                        "dataset_id": ds_id,
                        "repaired_tasks": [
                            {
                                "id": "t1",
                                "input": "def eval_input(x): exec(x)",
                                "expected_output": "INSECURE_EVAL",
                            },
                            {
                                "id": "t2",
                                "input": "def query_db(q): db.execute(q)",
                                "expected_output": "SQL_INJECTION",
                            },
                            {
                                "id": "t3",
                                "input": "def bad_format(): pass",
                                "expected_output": "NO_OP_SECURE",
                            },
                        ],
                    },
                    reasoning="Step 4a: Repair dataset tasks.",
                )
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="validate_benchmark_dataset",
                arguments={"dataset_id": ds_id},
                reasoning="Step 4b: Validate dataset tasks.",
            )

        # Step 5: Run target model executions
        if "run target model" in desc:
            bm_v_id = task.benchmark_version_id or "00000000-0000-0000-0000-000000000003"
            ds_v_id = task.dataset_version_id or "00000000-0000-0000-0000-000000000002"
            # If run has been dispatched but status isn't complete, perform get_run_status
            called_tools = [c.tool_name for c in task.tool_calls]
            if "run_benchmark" in called_tools and "get_run_status" not in called_tools:
                # Dynamically resolve execution ID
                real_exec_id = None
                for obs in task.observations:
                    if (
                        obs.tool_name == "run_benchmark"
                        and isinstance(obs.output, dict)
                        and "execution_ids" in obs.output
                    ):
                        real_exec_id = str(obs.output["execution_ids"][0])
                exec_id = real_exec_id or "00000000-0000-0000-0000-000000000004"
                return AgentDecision(
                    type=AgentDecisionType.TOOL_CALL,
                    tool_name="get_run_status",
                    arguments={"execution_id": exec_id},
                    reasoning="Step 5a: Poll execution run status.",
                )
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="run_benchmark",
                arguments={
                    "benchmark_version_id": bm_v_id,
                    "dataset_version_id": ds_v_id,
                    "target_models": ["mock"],
                },
                reasoning="Step 5b: Dispatch execution runs.",
            )

        # Step 6: Evaluate outputs using evaluation cases
        if "evaluate outputs" in desc:
            real_exec_id = None
            for obs in task.observations:
                if (
                    obs.tool_name == "run_benchmark"
                    and isinstance(obs.output, dict)
                    and "execution_ids" in obs.output
                ):
                    real_exec_id = str(obs.output["execution_ids"][0])
            exec_id = real_exec_id or "00000000-0000-0000-0000-000000000004"
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="evaluate_run",
                arguments={"execution_id": exec_id},
                reasoning="Step 6: Evaluate execution outputs.",
            )

        # Step 7: Publish comparative benchmark report
        if "publish comparative benchmark report" in desc:
            bm_id = task.benchmark_id or "00000000-0000-0000-0000-000000000001"
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="generate_report",
                arguments={
                    "benchmark_id": bm_id,
                    "title": "Python Vulnerability Detection Benchmark Evaluation Report",
                },
                reasoning="Step 7: Generate comparative summary report.",
            )

        return AgentDecision(
            type=AgentDecisionType.FINAL_RESPONSE,
            response="Could not determine next step.",
            reasoning="Fallback decision.",
        )
