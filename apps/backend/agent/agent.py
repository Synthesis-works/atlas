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

    def run_task(self, task: AgentTask, db: Session) -> AgentTask:
        """
        Executes the agent loop until the task completes, fails, pauses for approval, or hits a runtime limit.
        """
        if not task.started_at:
            task.started_at = datetime.now(UTC)

        if not task.plan:
            task.plan = self.planner.generate_initial_plan(task.goal)
            task.status = AgentTaskStatus.PLANNING
            task.add_trace("PLAN_GENERATED", {"plan_steps_count": len(task.plan)})

        task.status = AgentTaskStatus.EXECUTING

        while task.is_active():
            # Check hard runtime limits
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
                task.status = AgentTaskStatus.COMPLETED
                task.completed_at = datetime.now(UTC)
                task.final_result = {
                    "summary": decision.response,
                    "total_steps": task.step_count,
                    "total_tool_calls": task.total_tool_calls,
                }
                task.add_trace("TASK_COMPLETED", {"summary": decision.response})
                break

            elif decision.type == AgentDecisionType.FAIL:
                task.status = AgentTaskStatus.FAILED
                task.completed_at = datetime.now(UTC)
                task.error_detail = decision.error_message
                task.add_trace("TASK_FAILED", {"error": decision.error_message})
                break

        return task
