from typing import Any

from pydantic import BaseModel, Field


class Prompt(BaseModel):
    system: str = Field(default="", description="System instructions for the model")
    user: str = Field(..., description="User prompt or task")
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Optional metadata for the prompt"
    )
