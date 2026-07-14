from typing import Protocol, Optional, Dict, Any
from pydantic import BaseModel

class JudgeResponse(BaseModel):
    score: float
    reasoning: str
    metadata: Optional[Dict[str, Any]] = None

class JudgeProvider(Protocol):
    def evaluate(self, prompt: str, rubric: str) -> JudgeResponse:
        """Evaluates the prompt against the rubric and returns a response."""
        ...
