from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class PredictionResult(BaseModel):
    output_text: str
    latency_ms: int | None = None
    token_usage: int | None = None
    raw_response: Any | None = None


class BaseModelAdapter(ABC):
    @abstractmethod
    def predict(self, prompt_text: str) -> PredictionResult:
        """
        Takes a fully hydrated prompt text and returns a structured PredictionResult.
        """
        pass
