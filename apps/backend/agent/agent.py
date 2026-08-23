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
    MAX_CLARIFICATION_ROUNDS,
    MAX_EXECUTION_TIME,
    MAX_REPAIR_ATTEMPTS,
    MAX_STEPS,
    MAX_TOOL_CALLS,
    AgentDecision,
    AgentDecisionType,
    AgentTask,
    AgentTaskStatus,
    ObservationRecord,
)
from apps.backend.agent.tools.execution_tools import TERMINAL_EXECUTION_STATUSES
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

    def _normalize_clarification(self, text: str) -> str:
        import re

        if not text:
            return ""
        return re.sub(r"[^a-zA-Z0-9]", "", text).lower()

    def _get_clarification_question(self, decision: AgentDecision) -> Optional[str]:
        if decision.type == AgentDecisionType.REQUEST_CLARIFICATION:
            return decision.response or "Could you clarify your request?"
        elif (
            decision.type == AgentDecisionType.TOOL_CALL
            and decision.tool_name == "request_clarification"
        ):
            return decision.arguments.get("question") or "Could you clarify your request?"
        return None

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
                num = getattr(
                    s, "step_number", s.get("step_number") if isinstance(s, dict) else "?"
                )
                desc = getattr(
                    s, "description", s.get("description") if isinstance(s, dict) else ""
                )
                step_descs.append(f"Step {num}: {desc}")
            return (
                False,
                f"Task has {len(pending_steps)} unfulfilled plan steps ({', '.join(step_descs[:3])})",
            )

        # Check if report generation was requested/initiated
        has_run_benchmark = any(c.tool_name == "run_benchmark" for c in task.tool_calls)
        has_report_step = any("report" in getattr(s, "description", "").lower() for s in task.plan)

        if has_run_benchmark or has_report_step:
            if not task.report_id:
                return (
                    False,
                    "Task execution is not complete: target model executions were run or a report step was planned, but no report has been generated/published yet. You MUST call generate_report.",
                )

            # Verify the report and version explicitly exist in the database and belong to this run lineage
            import uuid
            from atlas_db.core.session import SessionLocal

            with SessionLocal() as db_session:
                from sqlalchemy import text

                # Retrieve the report_versions row (task.report_id is the ReportVersion.id)
                report_ver_hex = (
                    task.report_id.replace("-", "")
                    if isinstance(task.report_id, str)
                    else str(task.report_id).replace("-", "")
                )
                version_row = db_session.execute(
                    text(
                        "SELECT id, report_id, execution_id FROM report_versions WHERE id = :report_version_id"
                    ),
                    {"report_version_id": report_ver_hex},
                ).fetchone()

                if not version_row:
                    return (
                        False,
                        f"Report version '{task.report_id}' not found in the report_versions table.",
                    )

                # Retrieve the report row
                report_row = db_session.execute(
                    text("SELECT id, name, project_id FROM reports WHERE id = :report_id"),
                    {"report_id": version_row.report_id},
                ).fetchone()

                if not report_row:
                    return (
                        False,
                        f"Parent Report '{version_row.report_id}' not found in the reports table.",
                    )

                # Check execution run lineage
                if task.execution_ids:
                    if not version_row.execution_id:
                        return (
                            False,
                            f"Lineage error: Report version '{task.report_id}' has no execution_id link.",
                        )
                    version_exec_hex = (
                        version_row.execution_id.replace("-", "")
                        if isinstance(version_row.execution_id, str)
                        else str(version_row.execution_id).replace("-", "")
                    )
                    task_exec_hexs = [str(eid).replace("-", "") for eid in task.execution_ids]
                    if version_exec_hex not in task_exec_hexs:
                        return (
                            False,
                            f"Lineage error: Report version execution_id '{version_row.execution_id}' does not match any execution IDs for this task: {task.execution_ids}.",
                        )

        # If task requested benchmark creation/evaluation, check required DB artifacts / tool calls
        goal_lower = task.goal.lower()
        if any(
            k in goal_lower for k in ["benchmark", "dataset", "evaluate", "arithmetic", "solve"]
        ):
            if task.total_tool_calls == 0:
                return False, "Task requested benchmark execution but 0 tool calls were executed."

        return True, ""

    def run_task(self, task: AgentTask, db: Session) -> AgentTask:
        """
        Executes the agent loop until the task completes, fails, pauses for approval, or hits a runtime limit.
        """
        if task.status in (AgentTaskStatus.PENDING, AgentTaskStatus.PLANNING):
            task.status = AgentTaskStatus.EXECUTING
        task.started_at = datetime.now(UTC)
        task.add_trace(
            "TASK_STARTED", {"goal": task.goal, "primary_provider": task.primary_provider}
        )

        # Step 0: Plan Generation
        if not task.plan:
            task.plan = self.planner.generate_initial_plan(
                task.goal, getattr(task, "run_mode", None)
            )
            task.add_trace("PLAN_GENERATED", {"plan_steps_count": len(task.plan)})

        while task.status in (
            AgentTaskStatus.EXECUTING,
            AgentTaskStatus.REPAIRING,
            AgentTaskStatus.PLANNING,
            AgentTaskStatus.RESUMED,
            AgentTaskStatus.EVALUATING,
            AgentTaskStatus.REPORTING,
        ):
            old_fingerprint = self._get_progress_fingerprint(task)
            # Enforce hard limits
            if task.step_count >= MAX_STEPS:
                task.status = AgentTaskStatus.FAILED
                task.error_detail = f"Hard limit exceeded: step_count ({task.step_count}) >= MAX_STEPS ({MAX_STEPS})."
                task.add_trace("LIMIT_EXCEEDED", {"limit": "MAX_STEPS", "value": task.step_count})
                break

            if task.total_tool_calls >= MAX_TOOL_CALLS:
                task.status = AgentTaskStatus.FAILED
                task.error_detail = f"Hard limit exceeded: total_tool_calls ({task.total_tool_calls}) >= MAX_TOOL_CALLS ({MAX_TOOL_CALLS})."
                task.add_trace(
                    "LIMIT_EXCEEDED", {"limit": "MAX_TOOL_CALLS", "value": task.total_tool_calls}
                )
                break

            if task.repair_attempts >= MAX_REPAIR_ATTEMPTS:
                task.status = AgentTaskStatus.FAILED
                task.error_detail = f"Hard limit exceeded: repair_attempts ({task.repair_attempts}) >= MAX_REPAIR_ATTEMPTS ({MAX_REPAIR_ATTEMPTS})."
                task.add_trace(
                    "LIMIT_EXCEEDED",
                    {"limit": "MAX_REPAIR_ATTEMPTS", "value": task.repair_attempts},
                )
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
            task.add_trace(
                "DECISION_MADE",
                {"decision_type": decision.type.value, "reasoning": decision.reasoning},
            )

            # Uniform Clarification Check
            clarify_question = self._get_clarification_question(decision)
            if clarify_question is not None:
                fingerprint = self._normalize_clarification(clarify_question)

                # Check if we are already waiting for clarification
                if task.status == AgentTaskStatus.WAITING_FOR_CLARIFICATION:
                    break

                # Check if we have already answered this clarification
                previous_answer = None
                for item in task.past_clarifications:
                    if item.get("fingerprint") == fingerprint:
                        previous_answer = item.get("answer")
                        break
                if previous_answer is None and task.past_clarifications:
                    # Semantic fallback: if the model asks another framing/safety/proposing check
                    # but we already answered, reuse the user's primary decision response answer.
                    previous_answer = task.past_clarifications[-1].get("answer")

                if previous_answer is not None:
                    # Duplicate clarification! The user already answered this.
                    # Inject the answer back into context and continue execution without pausing.
                    task.add_trace(
                        "DUPLICATE_CLARIFICATION_REJECTED",
                        {
                            "question": clarify_question,
                            "fingerprint": fingerprint,
                            "previous_answer": previous_answer,
                        },
                    )
                    task.observations.append(
                        ObservationRecord(
                            call_id=f"clarify_dup_{task.step_count}",
                            tool_name="system_notice",
                            success=True,
                            output={
                                "notice": (
                                    f"You previously requested clarification: '{clarify_question}'. "
                                    f"The user has already answered this: '{previous_answer}'. "
                                    "Please proceed and execute the remaining benchmark/dataset tools using this answer."
                                )
                            },
                        )
                    )
                    continue

                # Check the max number of clarification attempts
                if task.clarification_attempts >= MAX_CLARIFICATION_ROUNDS:
                    task.status = AgentTaskStatus.FAILED
                    task.completed_at = datetime.now(UTC)
                    task.error_detail = (
                        f"Hard limit exceeded: clarification_attempts ({task.clarification_attempts}) "
                        f">= MAX_CLARIFICATION_ROUNDS ({MAX_CLARIFICATION_ROUNDS})."
                    )
                    task.add_trace(
                        "LIMIT_EXCEEDED",
                        {"limit": "MAX_CLARIFICATION_ROUNDS", "value": task.clarification_attempts},
                    )
                    break

                # Otherwise, pause execution and wait for clarification
                import uuid

                task.status = AgentTaskStatus.WAITING_FOR_CLARIFICATION
                task.clarification_request = clarify_question
                task.clarification_prompt = clarify_question
                task.clarification_id = f"clarify_{uuid.uuid4().hex[:8]}"
                task.clarification_requested_at = datetime.now(UTC)
                task.clarification_attempts += 1

                task.add_trace(
                    "WAITING_FOR_CLARIFICATION",
                    {
                        "question": clarify_question,
                        "clarification_id": task.clarification_id,
                        "attempt": task.clarification_attempts,
                    },
                )
                break

            if decision.type == AgentDecisionType.TOOL_CALL:
                tool_name = decision.tool_name
                if not tool_name:
                    continue
                args = decision.arguments

                # Permission check
                if not self.registry.check_permission(tool_name, task.granted_permissions):
                    task.status = AgentTaskStatus.WAITING_FOR_APPROVAL
                    task.pending_tool_call = {"tool_name": tool_name, "arguments": args}
                    task.approval_token = f"approval_{task.task_id.hex[:8]}"
                    task.add_trace(
                        "WAITING_FOR_APPROVAL",
                        {"tool_name": tool_name, "token": task.approval_token},
                    )
                    break

                # Execute tool
                obs, output = self.executor.execute_tool(task, db, tool_name, args)

                # Classify database/connection infrastructure failures
                if not obs.success and obs.error:
                    infra_keywords = [
                        "no such table",
                        "no such column",
                        "database is locked",
                        "unable to open database",
                        "connection refused",
                        "connection to database failed",
                        "actively refused",
                    ]
                    err_lower = obs.error.lower()
                    if any(k in err_lower for k in infra_keywords):
                        task.status = AgentTaskStatus.FAILED
                        task.completed_at = datetime.now(UTC)
                        task.error_detail = (
                            f"Infrastructure failure during tool '{tool_name}': {obs.error}"
                        )
                        task.add_trace("TASK_FAILED", {"error": task.error_detail})
                        break

                # Check validation failure diagnosis & repair loop transition
                if (
                    tool_name == "validate_benchmark_dataset"
                    and isinstance(output, dict)
                    and not output.get("valid", True)
                ):
                    task.status = AgentTaskStatus.REPAIRING
                    task.repair_attempts += 1
                    task.add_trace(
                        "REPAIR_TRIGGERED",
                        {
                            "repair_attempt": task.repair_attempts,
                            "invalid_count": output.get("invalid_count", 0),
                        },
                    )

                self.planner.update_plan_on_decision(task, decision, output)

                # First-class async-wait phase begins when remote runs are
                # dispatched. With an asynchronous execution backend (GitHub
                # Actions) the task PARKS here: status is persisted and this
                # process ends; the outbox sweep resumes it when every tracked
                # execution reaches a terminal state (event-driven resume).
                # Synchronous/local backends keep the inline bounded wait.
                if (
                    tool_name == "run_benchmark"
                    and isinstance(output, dict)
                    and output.get("status") == "DISPATCHED"
                    and task.execution_wait_started_at is None
                ):
                    task.execution_wait_started_at = datetime.now(UTC)
                    from apps.backend.config import settings as _agent_settings

                    if _agent_settings.execution_backend == "github_actions":
                        task.status = AgentTaskStatus.WAITING_FOR_EXECUTION
                        task.waiting_since = datetime.now(UTC)
                        task.add_trace(
                            "AGENT_TASK_WAITING",
                            {
                                "execution_ids": list(task.execution_ids),
                                "resume_mode": "event_driven",
                            },
                        )
                        break
                    task.add_trace(
                        "EXECUTION_WAIT_STARTED",
                        {"execution_ids": list(task.execution_ids)},
                    )

                # Phase markers for the documented lifecycle state machine:
                # RESUMED -> EVALUATING -> REPORTING -> COMPLETED.
                if tool_name == "evaluate_run" and isinstance(output, dict):
                    task.status = AgentTaskStatus.EVALUATING
                if (
                    tool_name == "generate_report"
                    and isinstance(output, dict)
                    and not output.get("published")
                ):
                    task.status = AgentTaskStatus.REPORTING

                # A wall-clock wait timeout is an explicit execution failure,
                # not an agent reasoning failure.
                if (
                    tool_name == "wait_for_runs"
                    and isinstance(output, dict)
                    and output.get("status") == "WAIT_TIMEOUT"
                ):
                    task.status = AgentTaskStatus.FAILED
                    task.completed_at = datetime.now(UTC)
                    task.error_detail = (
                        f"Execution wait timeout after {output.get('waited_seconds')}s: "
                        f"{output.get('message')}"
                    )
                    task.add_trace(
                        "EXECUTION_WAIT_TIMEOUT",
                        {
                            "non_terminal_execution_ids": output.get(
                                "non_terminal_execution_ids", []
                            ),
                            "waited_seconds": output.get("waited_seconds"),
                        },
                    )
                    break

                # Auto-complete task when generate_report succeeds
                if (
                    tool_name == "generate_report"
                    and output
                    and isinstance(output, dict)
                    and output.get("published")
                ):
                    task.status = AgentTaskStatus.COMPLETED
                    task.completed_at = datetime.now(UTC)
                    summary_msg = output.get(
                        "summary", "Benchmark evaluation completed successfully."
                    )
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
                    logger.warning(
                        f"Rejected premature FINAL_RESPONSE for task {task.task_id}: {reason}"
                    )
                    task.add_trace(
                        "DECISION_REJECTED_PROSE",
                        {
                            "reason": reason,
                            "provider": task.current_provider,
                            "response": decision.response,
                        },
                    )

                    if not hasattr(task, "_prose_repairs"):
                        task._prose_repairs = {}  # type: ignore[attr-defined]

                    current_p = task.current_provider or "default"
                    repair_count = task._prose_repairs.get(current_p, 0)  # type: ignore[attr-defined]

                    if repair_count < 1:
                        task._prose_repairs[current_p] = repair_count + 1  # type: ignore[attr-defined]
                        repair_msg = (
                            f"ATTENTION: Your previous response returned conversational text ('{(decision.response or '')[:120]}...') "
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
                        logger.error(
                            f"Provider '{current_p}' failed repair and produced prose again. Failing task."
                        )
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

            # Plan-Progress Invariant Check
            new_fingerprint = self._get_progress_fingerprint(task)
            if new_fingerprint == old_fingerprint:
                if self._execution_wait_in_progress(task):
                    # Sanctioned async-wait phase: backoff polling of dispatched
                    # remote runs is legitimate waiting, not a reasoning stall.
                    task.add_trace(
                        "EXECUTION_WAIT_POLL",
                        {"consecutive_cycles": task.consecutive_non_progress_steps},
                    )
                else:
                    task.consecutive_non_progress_steps += 1
                    if task.consecutive_non_progress_steps >= 4:
                        task.status = AgentTaskStatus.FAILED
                        task.completed_at = datetime.now(UTC)
                        task.error_detail = (
                            "Plan-Progress Invariant Violation: The agent failed to advance the plan, "
                            "resolve a clarification, or produce a final result within 4 consecutive reasoning cycles. "
                            "Stopping execution to prevent infinite loop."
                        )
                        task.add_trace(
                            "PROGRESS_INVARIANT_VIOLATION",
                            {"consecutive_cycles": task.consecutive_non_progress_steps},
                        )
                        break
            else:
                task.consecutive_non_progress_steps = 0

        return task

    def _get_progress_fingerprint(self, task: AgentTask) -> tuple:
        """
        Computes a stable fingerprint representing the task's progress state.
        If the fingerprint remains unchanged across consecutive reasoning cycles,
        it indicates that no meaningful progress has been made.
        """
        plan_statuses = tuple(getattr(s, "status", "") for s in task.plan)
        past_clars_count = len(task.past_clarifications)
        clarification_id = task.clarification_id
        execution_ids = tuple(task.execution_ids)
        report_id = task.report_id

        # Serialize unique tool calls (tool name + normalized sorted arguments)
        unique_calls = []
        for c in task.tool_calls:
            args_key = tuple(sorted((k, str(v)) for k, v in c.arguments.items()))
            unique_calls.append((c.tool_name, args_key))
        unique_calls_set = tuple(sorted(list(set(unique_calls))))

        # Observed execution-state snapshot: latest successful get_run_status /
        # wait_for_runs result per execution. With async execution backends
        # (GitHub Actions), polling is legitimate progress whenever the observed
        # state changes (QUEUED -> RUNNING -> COMPLETED), even though tool
        # arguments repeat. Static states keep this component stable; genuinely
        # stuck loops outside the sanctioned wait phase still trip the invariant.
        exec_state: dict[str, tuple] = {}

        def _record(eid: str, snap: dict) -> None:
            if eid:
                exec_state[eid] = (
                    str(snap.get("status", "")),
                    str(snap.get("progress", "")),
                    snap.get("completed_items"),
                    snap.get("total_items"),
                )

        for obs in task.observations:
            tool_name = getattr(obs, "tool_name", None)
            if tool_name not in ("get_run_status", "wait_for_runs"):
                continue
            if not getattr(obs, "success", False):
                continue
            out = getattr(obs, "output", None)
            if not isinstance(out, dict):
                continue
            if tool_name == "wait_for_runs":
                per_exec = out.get("executions")
                if isinstance(per_exec, dict):
                    for eid, snap in per_exec.items():
                        if isinstance(snap, dict):
                            _record(str(eid), snap)
                continue
            _record(str(out.get("execution_id", "")), out)
        execution_state_snapshot = tuple(sorted(exec_state.items()))

        return (
            plan_statuses,
            past_clars_count,
            clarification_id,
            execution_ids,
            report_id,
            unique_calls_set,
            execution_state_snapshot,
        )

    def _execution_wait_in_progress(self, task: AgentTask) -> bool:
        """
        True while the task is legitimately waiting on dispatched async runs.

        Sanctioned waiting requires ALL of:
        - runs were dispatched (execution_wait_started_at set) and tracked,
        - the current cycle's action was a polling/waiting tool,
        - the wall-clock wait deadline has not been exceeded,
        - at least one tracked execution is still non-terminal.

        Terminal-but-static re-polling and post-deadline polling stay
        punishable by the Plan-Progress Invariant.
        """
        from apps.backend.config import settings

        if not task.execution_ids or task.execution_wait_started_at is None:
            return False
        if not task.tool_calls or task.tool_calls[-1].tool_name not in (
            "get_run_status",
            "wait_for_runs",
        ):
            return False

        started = task.execution_wait_started_at
        elapsed = (datetime.now(UTC) - started).total_seconds()
        if elapsed > settings.agent_execution_wait_deadline_seconds:
            return False

        latest: dict[str, str] = {}
        for obs in task.observations:
            tool_name = getattr(obs, "tool_name", None)
            if tool_name not in ("get_run_status", "wait_for_runs"):
                continue
            if not getattr(obs, "success", False):
                continue
            out = getattr(obs, "output", None)
            if not isinstance(out, dict):
                continue
            if tool_name == "get_run_status":
                eid = str(out.get("execution_id", ""))
                if eid:
                    latest[eid] = str(out.get("status", ""))
            else:
                per_exec = out.get("executions")
                if isinstance(per_exec, dict):
                    for eid, snap in per_exec.items():
                        if isinstance(snap, dict):
                            latest[str(eid)] = str(snap.get("status", ""))

        tracked = {str(e) for e in task.execution_ids}
        known = {eid: st for eid, st in latest.items() if eid in tracked}
        if not known:
            return False
        return any(st not in TERMINAL_EXECUTION_STATUSES for st in known.values())
