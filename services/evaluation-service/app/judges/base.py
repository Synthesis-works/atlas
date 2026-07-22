from typing import Any, Protocol

from pydantic import BaseModel


class JudgeResponse(BaseModel):
    score: float
    reasoning: str
    metadata: dict[str, Any] | None = None


class JudgeProvider(Protocol):
    def evaluate(self, prompt: str, rubric: str) -> JudgeResponse:
        """Evaluates the prompt against the rubric and returns a response."""
        ...
