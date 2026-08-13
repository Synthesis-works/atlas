from typing import Any
from sqlalchemy.orm import Session
from apps.backend.agent.state import AgentPermission
from apps.backend.agent.tools.base import BaseTool


class RequestClarificationTool(BaseTool):
    name = "request_clarification"
    description = (
        "Use this tool to ask the user for clarification when the task goal is ambiguous, "
        "underspecified, or if you need additional information (like which models to benchmark or the dataset format) "
        "before you can continue."
    )
    required_permission = AgentPermission.READ
    parameters_schema = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The clarification question/prompt to present to the user.",
            }
        },
        "required": ["question"],
    }

    def execute(self, db: Session, **kwargs: Any) -> Any:
        return {"suspended": True, "question": kwargs.get("question")}
