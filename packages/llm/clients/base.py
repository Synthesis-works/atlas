from abc import ABC, abstractmethod
from typing import List
from ..models.types import ModelInfo
from ..models.prompt import Prompt
from ..models.response import LLMResponse

class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def health(self) -> bool:
        """Check if the provider server/API is available."""
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """List available models."""
        pass

    @abstractmethod
    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        """Generate a completion for the given prompt."""
        pass

    @abstractmethod
    def stream_generate(self, model: str, prompt: Prompt, **kwargs):
        """Stream a completion for the given prompt."""
        raise NotImplementedError("Streaming is not yet supported.")

    def supports_streaming(self) -> bool:
        return False

    def supports_embeddings(self) -> bool:
        return False

    def supports_chat(self) -> bool:
        return False

    def supports_completion(self) -> bool:
        return True
