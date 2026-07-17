from pydantic import BaseModel
from typing import Optional, Any
from abc import ABC, abstractmethod

class PredictionResult(BaseModel):
    output_text: str
    latency_ms: Optional[int] = None
    token_usage: Optional[int] = None
    raw_response: Optional[Any] = None

class BaseModelAdapter(ABC):
    @abstractmethod
    def predict(self, prompt_text: str) -> PredictionResult:
        """
        Takes a fully hydrated prompt text and returns a structured PredictionResult.
        """
        pass
