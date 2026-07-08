from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class Prompt(BaseModel):
    system: str = Field(..., description="System instructions for the model")
    user: str = Field(..., description="User prompt or task")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata for the prompt")
