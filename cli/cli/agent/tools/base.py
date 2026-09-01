"""Client-side agent tool layer (Phase 2) — base abstractions.

The agent's tools expose Atlas capabilities **through the existing
``AtlasClient``** — never raw HTTP, shell, or filesystem access.  Each tool:

    LLM tool call
        -> validated tool arguments
        -> existing AtlasClient method
        -> DTO/result
        -> compact, bounded observation returned to the agent

Read vs write is explicit via :class:`AgentPermission` so Phase 4's REPL can
gate mutating operations.  This mirrors ``apps/backend/agent/tools/base.py`` but
is scoped to the client-side CLI and delegates to the SDK instead of a DB.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class AgentPermission(StrEnum):
    """Read/write classification for a tool's effect on Atlas state.

    ``WRITE`` marks tools that mutate Atlas state (creating/running executions,
    overwriting local files on export) and must be confirmed in the REPL.
    """

    READ = "READ"
    WRITE = "WRITE"


class ToolResult(BaseModel):
    """Compact, bounded observation returned to the agent after a tool run.

    ``summary`` is a short human/LLM-readable line (never a full API dump).
    ``data`` carries a small structured payload (bounded); ``error`` carries a
    message on failure and ``ok`` is False.
    """

    ok: bool = True
    summary: str
    data: dict[str, Any] | None = None
    error: str | None = None


class BaseTool(ABC):
    """Base class for a client-side Atlas agent tool.

    Subclasses declare a name, description, permission, and an OpenAPI-style
    ``parameters_schema`` (JSON Schema shaped like the backend's tools), then
    implement :meth:`execute` to delegate to one or more ``AtlasClient`` methods
    and return a :class:`ToolResult`.
    """

    name: str
    description: str
    required_permission: AgentPermission = AgentPermission.READ
    parameters_schema: dict[str, Any]

    def get_gemini_schema(self) -> dict[str, Any]:
        """Convert the OpenAPI-style schema to a Gemini functionDeclaration."""
        props = self.parameters_schema.get("properties", {})
        required = self.parameters_schema.get("required", [])

        gemini_props: dict[str, Any] = {}
        for prop_name, prop_spec in props.items():
            raw_type = str(prop_spec.get("type", "string")).upper()
            prop_dict: dict[str, Any] = {
                "description": prop_spec.get("description", ""),
            }
            if raw_type == "ARRAY":
                prop_dict["type"] = "ARRAY"
                items_spec = prop_spec.get("items")
                if isinstance(items_spec, dict):
                    prop_dict["items"] = {
                        "type": str(items_spec.get("type", "string")).upper()
                    }
            elif raw_type in {"OBJECT", "INTEGER", "BOOLEAN", "NUMBER"}:
                prop_dict["type"] = raw_type
            else:
                prop_dict["type"] = "STRING"
            gemini_props[prop_name] = prop_dict

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": gemini_props,
                "required": required,
            },
        }

    @abstractmethod
    def execute(self, client: Any, **kwargs: Any) -> ToolResult:
        """Validate arguments, call an ``AtlasClient`` method, return a result.

        ``client`` is an :class:`AtlasClient`-compatible object (a real client or
        a test double).  Implementations must validate/coerce arguments, delegate
        to SDK methods, and normalize the DTO/result into a compact
        :class:`ToolResult`.
        """
