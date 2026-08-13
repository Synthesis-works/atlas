import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from apps.backend.agent.state import AgentPermission
from apps.backend.agent.tools.base import BaseTool
from apps.backend.agent.tools.benchmark_tools import CreateBenchmarkTool, GetBenchmarkTool, SearchBenchmarksTool
from apps.backend.agent.tools.dataset_tools import CreateDatasetTool, GetDatasetTool, UpdateDatasetTool, ValidateBenchmarkDatasetTool
from apps.backend.agent.tools.evaluation_tools import CompareResultsTool, CreateEvaluationCaseTool, EvaluateRunTool, GenerateReportTool
from apps.backend.agent.tools.execution_tools import GetAvailableModelsTool, GetRunStatusTool, RunBenchmarkTool
from apps.backend.agent.tools.memory_tools import SearchMemoryTool
from apps.backend.agent.tools.clarification_tool import RequestClarificationTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for Atlas Agent tools.
    Handles tool discovery, Gemini functionDeclaration formatting, permission verification, and execution.
    """

    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        default_tools = [
            GetAvailableModelsTool(),
            SearchBenchmarksTool(),
            GetBenchmarkTool(),
            GetDatasetTool(),
            CreateBenchmarkTool(),
            CreateDatasetTool(),
            CreateEvaluationCaseTool(),
            UpdateDatasetTool(),
            ValidateBenchmarkDatasetTool(),
            RunBenchmarkTool(),
            GetRunStatusTool(),
            EvaluateRunTool(),
            CompareResultsTool(),
            GenerateReportTool(),
            SearchMemoryTool(),
            RequestClarificationTool(),
        ]
        for tool in default_tools:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "required_permission": t.required_permission.value,
                "parameters": t.parameters_schema,
            }
            for t in self.tools.values()
        ]

    def get_gemini_declarations(self) -> list[dict[str, Any]]:
        """
        Returns all tool schemas formatted as Gemini functionDeclarations.
        """
        return [t.get_gemini_schema() for t in self.tools.values()]

    def check_permission(self, tool_name: str, granted_permissions: list[AgentPermission]) -> bool:
        tool = self.get_tool(tool_name)
        if not tool:
            return False
        return tool.required_permission in granted_permissions

    def execute(self, tool_name: str, db: Session, arguments: dict[str, Any], **kwargs: Any) -> Any:
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' is not registered in ToolRegistry.")
        return tool.execute(db=db, **arguments, **kwargs)
