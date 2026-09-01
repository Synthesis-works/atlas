"""Client-side agent tool registry (Phase 2).

Discovers tools, formats them as Gemini functionDeclarations, classifies read
vs write (mutation), and dispatches validated tool calls to the
``AtlasClient``.  Mirrors ``apps/backend/agent/tools/registry.py`` but scoped to
the client-side CLI tools and delegating to the SDK instead of a DB session.
"""

from __future__ import annotations

from typing import Any

from cli.agent.tools.base import AgentPermission, BaseTool, ToolResult
from cli.agent.tools.library import (
    ExportReportTool,
    GetActivityTool,
    GetBenchmarkVersionsTool,
    GetDashboardTool,
    GetHealthTool,
    GetLeaderboardTool,
    GetModelSummaryTool,
    GetReportTool,
    GetRunTool,
    ListBenchmarksTool,
    ListModelsTool,
    SubmitRunTool,
    WatchRunTool,
    WhoAmITool,
)


class ToolRegistry:
    """Central registry of client-side agent tools."""

    def __init__(self, tools: list[BaseTool] | None = None) -> None:
        self._tools: dict[str, BaseTool] = {}
        for tool in tools or self._default_tools():
            self.register(tool)

    @staticmethod
    def _default_tools() -> list[BaseTool]:
        return [
            ListBenchmarksTool(),
            GetBenchmarkVersionsTool(),
            ListModelsTool(),
            SubmitRunTool(),
            GetRunTool(),
            WatchRunTool(),
            GetReportTool(),
            ExportReportTool(),
            GetLeaderboardTool(),
            GetModelSummaryTool(),
            GetActivityTool(),
            GetDashboardTool(),
            GetHealthTool(),
            WhoAmITool(),
        ]

    @property
    def registry(self) -> dict[str, BaseTool]:
        return self._tools

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "required_permission": t.required_permission.value,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        ]

    def get_gemini_declarations(self) -> list[dict[str, Any]]:
        """All tool schemas as Gemini ``functionDeclarations``."""
        return [t.get_gemini_schema() for t in self._tools.values()]

    def is_mutating(self, tool_name: str) -> bool:
        """True when the named tool mutates state (WRITE) and needs confirmation."""
        tool = self._tools.get(tool_name)
        return bool(tool and tool.required_permission is AgentPermission.WRITE)

    def execute(self, tool_name: str, client: Any, arguments: dict[str, Any]) -> ToolResult:
        """Validate and dispatch a tool call to the given AtlasClient."""
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' is not registered in ToolRegistry.")
        return tool.execute(client=client, **arguments)
