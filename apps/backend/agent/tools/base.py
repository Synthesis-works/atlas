from abc import ABC, abstractmethod
from typing import Any, Dict
from sqlalchemy.orm import Session

from apps.backend.agent.state import AgentPermission


class BaseTool(ABC):
    name: str
    description: str
    required_permission: AgentPermission = AgentPermission.READ
    parameters_schema: dict[str, Any]  # OpenAPI / JSON Schema format

    def get_gemini_schema(self) -> dict[str, Any]:
        """
        Converts OpenAPI / JSON schema parameters into Gemini functionDeclaration schema format.
        """
        props = self.parameters_schema.get("properties", {})
        required = self.parameters_schema.get("required", [])
        
        gemini_props = {}
        for prop_name, prop_spec in props.items():
            raw_type = prop_spec.get("type", "string").upper()
            prop_dict: dict[str, Any] = {
                "description": prop_spec.get("description", ""),
            }

            if raw_type == "ARRAY":
                prop_dict["type"] = "ARRAY"
                items_spec = prop_spec.get("items", {})
                item_type = items_spec.get("type", "string").upper() if isinstance(items_spec, dict) else "STRING"
                prop_dict["items"] = {"type": item_type}
            elif raw_type in {"OBJECT", "INTEGER", "BOOLEAN"}:
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
    def execute(self, db: Session, **kwargs: Any) -> Any:
        """
        Executes tool routine against Atlas database / application services.
        """
        pass
