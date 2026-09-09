import logging
import uuid
from typing import Any, Dict, Tuple
from sqlalchemy.orm import Session

from apps.backend.agent.state import AgentPermission, AgentTask, ObservationRecord, ToolCallRecord
from apps.backend.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Safely executes tool routines, enforces permissions, formats sanitized observations, and logs execution traces.
    """

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or ToolRegistry()

    def execute_tool(
        self, task: AgentTask, db: Session, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[ObservationRecord, Any]:
        call_id = str(uuid.uuid4())
        call_rec = ToolCallRecord(call_id=call_id, tool_name=tool_name, arguments=arguments)
        task.tool_calls.append(call_rec)
        task.total_tool_calls += 1

        # Check permissions
        if not self.registry.check_permission(tool_name, task.granted_permissions):
            tool = self.registry.get_tool(tool_name)
            req_perm = tool.required_permission.value if tool else "UNKNOWN"
            err_msg = f"Task permission denied for tool '{tool_name}'. Required: {req_perm}"
            obs = ObservationRecord(
                call_id=call_id, tool_name=tool_name, success=False, output=None, error=err_msg
            )
            task.observations.append(obs)
            task.add_trace("TOOL_PERMISSION_DENIED", {"tool_name": tool_name, "error": err_msg})
            return obs, None

        try:
            from apps.backend.agent.scope import ToolScopeEnforcer

            tool = self.registry.get_tool(tool_name)
            if tool is None:
                raise ValueError(f"Tool '{tool_name}' not found in registry")
            ToolScopeEnforcer(db).enforce(task, tool, arguments)

            scope_kwargs: dict[str, Any] = {}
            if task.created_by_user_id is not None:
                scope_kwargs["user_id"] = str(task.created_by_user_id)
            if task.organization_id is not None:
                scope_kwargs["organization_id"] = str(task.organization_id)

            output = self.registry.execute(
                tool_name=tool_name,
                db=db,
                arguments=arguments,
                project_id=task.project_id,
                task_id=str(task.task_id),
                **scope_kwargs,
            )
            obs = ObservationRecord(
                call_id=call_id, tool_name=tool_name, success=True, output=output
            )
            task.observations.append(obs)

            # Explicit Data Lineage Assignment
            if isinstance(output, dict):
                if tool_name == "create_benchmark":
                    if output.get("id"):
                        task.benchmark_id = str(output["id"])
                    if output.get("version_id"):
                        task.benchmark_version_id = str(output["version_id"])
                elif tool_name == "create_dataset":
                    if output.get("id"):
                        task.dataset_id = str(output["id"])
                    if output.get("version_id"):
                        task.dataset_version_id = str(output["version_id"])
                elif tool_name == "run_benchmark":
                    if output.get("execution_ids"):
                        task.execution_ids = [str(e) for e in output["execution_ids"]]
                elif tool_name == "generate_report":
                    if output.get("report_id"):
                        task.report_id = str(output["report_id"])

            task.add_trace(
                "TOOL_EXECUTION_SUCCESS",
                {"tool_name": tool_name, "arguments": arguments, "output": output},
            )
            return obs, output

        except Exception as e:
            err_str = str(e)
            logger.error(f"Execution of tool '{tool_name}' failed: {err_str}")
            obs = ObservationRecord(
                call_id=call_id, tool_name=tool_name, success=False, output=None, error=err_str
            )
            task.observations.append(obs)
            task.add_trace("TOOL_EXECUTION_ERROR", {"tool_name": tool_name, "error": err_str})
            return obs, None
