from datetime import datetime, timezone, UTC
import logging
from typing import Optional
from sqlalchemy.orm import Session

from apps.backend.agent.executor import ToolExecutor
from apps.backend.agent.memory import AgentMemoryManager
from apps.backend.agent.planner import AgentPlanner
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.mock import MockAgentProvider
from apps.backend.agent.state import (
    MAX_EXECUTION_TIME,
    MAX_REPAIR_ATTEMPTS,
    MAX_STEPS,
    MAX_TOOL_CALLS,
    AgentDecisionType,
    AgentTask,
    AgentTaskStatus,
    ObservationRecord,
)
from apps.backend.agent.tools.registry import ToolRegistry

from apps.backend.agent.providers.router import ProviderRouter

logger = logging.getLogger(__name__)


class AtlasAgent:
    """
    Main Atlas Agent loop driving autonomous benchmark & evaluation orchestration.
    Enforces hard safety limits, deterministic state machine transitions, and permission boundaries.
    """

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        registry: Optional[ToolRegistry] = None,
        planner: Optional[AgentPlanner] = None,
        executor: Optional[ToolExecutor] = None,
        memory_manager: Optional[AgentMemoryManager] = None,
    ):
        self.provider = provider or ProviderRouter()
        self.registry = registry or ToolRegistry()
        self.planner = planner or AgentPlanner()
        self.executor = executor or ToolExecutor(registry=self.registry)
        self.memory_manager = memory_manager or AgentMemoryManager()

    def _validate_completion(self, task: AgentTask, decision: AgentDecision) -> tuple[bool, str]:
        """
        Validates whether a FINAL_RESPONSE decision is allowed to complete the task.
        Returns (is_valid, reason).
        """
        if decision.type != AgentDecisionType.FINAL_RESPONSE:
            return True, ""

        # Check if plan contains pending steps
        pending_steps = []
        for s in task.plan:
            status = getattr(s, "status", s.get("status") if isinstance(s, dict) else None)
            if status == "PENDING":
                pending_steps.append(s)

        if pending_steps:
            step_descs = []
            for s in pending_steps:
                num = getattr(s, "step_number", s.get("step_number") if isinstance(s, dict) else "?")
                desc = getattr(s, "description", s.get("description") if isinstance(s, dict) else "")
                step_descs.append(f"Step {num}: {desc}")
            return False, f"Task has {len(pending_steps)} unfulfilled plan steps ({', '.join(step_descs[:3])})"

        # If task requested benchmark creation/evaluation, check required DB artifacts / tool calls
        goal_lower = task.goal.lower()
        if any(k in goal_lower for k in ["benchmark", "dataset", "evaluate", "arithmetic", "solve"]):
            if task.total_tool_calls == 0:
                return False, "Task requested benchmark execution but 0 tool calls were executed."

        return True, ""

    def run_task(self, task: AgentTask, db: Session) -> AgentTask:
        """
        Executes the agent loop until the task completes, fails, pauses for approval, or hits a runtime limit.
        """
        task.status = AgentTaskStatus.EXECUTING
        task.started_at = datetime.now(UTC)
        task.add_trace("TASK_STARTED", {"goal": task.goal, "primary_provider": task.primary_provider})

        # Step 0: Plan Generation
        if not task.plan:
            task.plan = self.planner.generate_initial_plan(task.goal)
            task.add_trace("PLAN_GENERATED", {"plan_steps_count": len(task.plan)})

        while task.status in (AgentTaskStatus.EXECUTING, AgentTaskStatus.REPAIRING):
            # Enforce hard limits
            if task.step_count >= MAX_STEPS:
                task.status = AgentTaskStatus.FAILED
                task.error_detail = f"Hard limit exceeded: step_count ({task.step_count}) >= MAX_STEPS ({MAX_STEPS})."
                task.add_trace("LIMIT_EXCEEDED", {"limit": "MAX_STEPS", "value": task.step_count})
                break

            if task.total_tool_calls >= MAX_TOOL_CALLS:
                task.status = AgentTaskStatus.FAILED
                task.error_detail = f"Hard limit exceeded: total_tool_calls ({task.total_tool_calls}) >= MAX_TOOL_CALLS ({MAX_TOOL_CALLS})."
                task.add_trace("LIMIT_EXCEEDED", {"limit": "MAX_TOOL_CALLS", "value": task.total_tool_calls})
                break

            if task.repair_attempts >= MAX_REPAIR_ATTEMPTS:
                task.status = AgentTaskStatus.FAILED
                task.error_detail = f"Hard limit exceeded: repair_attempts ({task.repair_attempts}) >= MAX_REPAIR_ATTEMPTS ({MAX_REPAIR_ATTEMPTS})."
                task.add_trace("LIMIT_EXCEEDED", {"limit": "MAX_REPAIR_ATTEMPTS", "value": task.repair_attempts})
                break

            elapsed = (datetime.now(UTC) - task.started_at).total_seconds()
            if elapsed > MAX_EXECUTION_TIME:
                task.status = AgentTaskStatus.FAILED
                task.error_detail = f"Hard execution timeout: elapsed ({int(elapsed)}s) > MAX_EXECUTION_TIME ({MAX_EXECUTION_TIME}s)."
                task.add_trace("LIMIT_EXCEEDED", {"limit": "MAX_EXECUTION_TIME", "value": elapsed})
                break

            task.step_count += 1
            prompt_context = self.memory_manager.build_prompt_context(task)
            declarations = self.registry.get_gemini_declarations()

            # LLM Decision Step
            decision = self.provider.decide(task, prompt_context, declarations)
            task.add_trace("DECISION_MADE", {"decision_type": decision.type.value, "reasoning": decision.reasoning})

            if decision.type == AgentDecisionType.TOOL_CALL:
                tool_name = decision.tool_name
                args = decision.arguments

                # Permission check
                if not self.registry.check_permission(tool_name, task.granted_permissions):
                    task.status = AgentTaskStatus.WAITING_FOR_APPROVAL
                    task.pending_tool_call = {"tool_name": tool_name, "arguments": args}
                    task.approval_token = f"approval_{task.task_id.hex[:8]}"
                    task.add_trace("WAITING_FOR_APPROVAL", {"tool_name": tool_name, "token": task.approval_token})
                    break

                # Execute tool
                obs, output = self.executor.execute_tool(task, db, tool_name, args)

                # Check validation failure diagnosis & repair loop transition
                if tool_name == "validate_benchmark_dataset" and isinstance(output, dict) and not output.get("valid", True):
                    task.status = AgentTaskStatus.REPAIRING
                    task.repair_attempts += 1
                    task.add_trace("REPAIR_TRIGGERED", {"repair_attempt": task.repair_attempts, "invalid_count": output.get("invalid_count", 0)})

                self.planner.update_plan_on_decision(task, decision, output)

                # Auto-complete task when generate_report succeeds
                if tool_name == "generate_report" and output and isinstance(output, dict) and output.get("published"):
                    task.status = AgentTaskStatus.COMPLETED
                    task.completed_at = datetime.now(UTC)
                    summary_msg = output.get("summary", "Benchmark evaluation completed successfully.")
                    task.final_result = {
                        "summary": summary_msg,
                        "total_steps": task.step_count,
                        "total_tool_calls": task.total_tool_calls,
                    }
                    task.add_trace("TASK_COMPLETED", {"summary": summary_msg})
                    break

            elif decision.type == AgentDecisionType.FINAL_RESPONSE:
                is_valid_completion, reason = self._validate_completion(task, decision)

                if is_valid_completion:
                    task.status = AgentTaskStatus.COMPLETED
                    task.completed_at = datetime.now(UTC)
                    task.final_result = {
                        "summary": decision.response,
                        "total_steps": task.step_count,
                        "total_tool_calls": task.total_tool_calls,
                    }
                    task.add_trace("TASK_COMPLETED", {"summary": decision.response})
                    break
                else:
                    logger.warning(f"Rejected premature FINAL_RESPONSE for task {task.task_id}: {reason}")
                    task.add_trace("DECISION_REJECTED_PROSE", {"reason": reason, "provider": task.current_provider, "response": decision.response})

                    if not hasattr(task, "_prose_repairs"):
                        task._prose_repairs = {}

                    current_p = task.current_provider or "default"
                    repair_count = task._prose_repairs.get(current_p, 0)

                    if repair_count < 1:
                        task._prose_repairs[current_p] = repair_count + 1
                        repair_msg = (
                            f"ATTENTION: Your previous response returned conversational text ('{decision.response[:120]}...') "
                            f"instead of executing a required tool call. The task is NOT complete: {reason}. "
                            "You MUST select and execute the next required tool call (e.g. create_benchmark). Do NOT return conversational text."
                        )
                        task.observations.append(
                            ObservationRecord(
                                call_id=f"call_repair_{task.step_count}",
                                tool_name="system_notice",
                                success=False,
                                output={"error": repair_msg},
                                error=repair_msg,
                            )
                        )
                        continue
                    else:
                        logger.error(f"Provider '{current_p}' failed repair and produced prose again. Failing task.")
                        task.status = AgentTaskStatus.FAILED
                        task.completed_at = datetime.now(UTC)
                        task.error_detail = f"All configured providers failed to produce a valid Atlas tool decision. Provider '{current_p}' returned conversational text instead of executable tool call: {reason}"
                        task.add_trace("TASK_FAILED", {"error": task.error_detail})
                        break

            elif decision.type == AgentDecisionType.FAIL:
                task.status = AgentTaskStatus.FAILED
                task.completed_at = datetime.now(UTC)
                task.error_detail = decision.error_message
                task.add_trace("TASK_FAILED", {"error": decision.error_message})
                break

        return task
