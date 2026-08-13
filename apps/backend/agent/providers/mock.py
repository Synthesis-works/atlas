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
        called_tools = [c.tool_name for c in task.tool_calls]

        # Check last observation for dataset validation failure simulation
        last_obs = task.observations[-1] if task.observations else None

        # Mock clarification trigger
        has_active_clarification = (
            task.status == "WAITING_FOR_CLARIFICATION" or task.clarification_id is not None
        )
        has_answered_clarification = (
            task.clarification_answer is not None or len(task.past_clarifications) > 0
        )
        if (
            "clarif" in task.goal.lower()
            and not has_active_clarification
            and not has_answered_clarification
        ):
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="request_clarification",
                arguments={"question": "Should we test addition or subtraction?"},
                reasoning="Goal is ambiguous. Ask for clarification.",
            )

        if "create_benchmark" not in called_tools:
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

        if "create_dataset" not in called_tools:
            # Get created benchmark ID from last observation if available
            bm_id = "00000000-0000-0000-0000-000000000001"
            if last_obs and isinstance(last_obs.output, dict) and "id" in last_obs.output:
                bm_id = str(last_obs.output["id"])

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

        if "validate_benchmark_dataset" not in called_tools:
            ds_id = "00000000-0000-0000-0000-000000000002"
            if last_obs and isinstance(last_obs.output, dict) and "id" in last_obs.output:
                ds_id = str(last_obs.output["id"])

            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="validate_benchmark_dataset",
                arguments={"dataset_id": ds_id},
                reasoning="Step 3: Validate dataset tasks format and completeness.",
            )

        # Handle validation recovery flow
        if (
            called_tools.count("validate_benchmark_dataset") == 1
            and "update_dataset" not in called_tools
        ):
            ds_id = "00000000-0000-0000-0000-000000000002"
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
                reasoning="Step 4: Repair dataset task t3 missing expected output.",
            )

        if (
            called_tools.count("validate_benchmark_dataset") == 1
            and "update_dataset" in called_tools
        ):
            ds_id = "00000000-0000-0000-0000-000000000002"
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="validate_benchmark_dataset",
                arguments={"dataset_id": ds_id},
                reasoning="Step 5: Re-validate repaired dataset.",
            )

        if "run_benchmark" not in called_tools:
            bm_v_id = "00000000-0000-0000-0000-000000000003"
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="run_benchmark",
                arguments={
                    "benchmark_version_id": bm_v_id,
                    "target_models": ["gemini-2.5-flash", "mock-gpt-4o"],
                },
                reasoning="Step 6: Dispatch execution runs against target models.",
            )

        if "get_run_status" not in called_tools:
            exec_id = "00000000-0000-0000-0000-000000000004"
            if (
                last_obs
                and isinstance(last_obs.output, dict)
                and "execution_ids" in last_obs.output
            ):
                exec_id = str(last_obs.output["execution_ids"][0])
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="get_run_status",
                arguments={"execution_id": exec_id},
                reasoning="Step 7: Poll execution run status.",
            )

        if "evaluate_run" not in called_tools:
            exec_id = "00000000-0000-0000-0000-000000000004"
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="evaluate_run",
                arguments={"execution_id": exec_id},
                reasoning="Step 8: Evaluate execution outputs.",
            )

        if "generate_report" not in called_tools:
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name="generate_report",
                arguments={
                    "benchmark_id": "00000000-0000-0000-0000-000000000001",
                    "title": "Python Vulnerability Detection Benchmark Evaluation Report",
                },
                reasoning="Step 9: Generate comparative summary report.",
            )

        # All steps completed!
        return AgentDecision(
            type=AgentDecisionType.FINAL_RESPONSE,
            response=(
                "Benchmark workflow completed successfully!\n"
                "- Created Python Vulnerability Detection Benchmark\n"
                "- Dataset attached, 1 invalid sample repaired, validation passed\n"
                "- Dispatched executions for 2 models\n"
                "- Evaluation completed & report generated."
            ),
            reasoning="All steps completed.",
        )
