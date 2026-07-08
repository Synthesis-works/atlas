from typing import Dict, Optional
from .base import BaseLLMClient
from .ollama import OllamaClient
from ..models.prompt import Prompt
from ..models.response import LLMResponse
from ..exceptions import LLMError

class ProviderAdapter:
    """Routes requests from Atlas to the appropriate provider client."""

    def __init__(self):
        self.clients: Dict[str, BaseLLMClient] = {
            "ollama": OllamaClient()
        }

    def register_client(self, provider: str, client: BaseLLMClient):
        """Register a new provider client."""
        self.clients[provider] = client

    def get_client(self, provider: str) -> BaseLLMClient:
        client = self.clients.get(provider)
        if not client:
            raise ValueError(f"Provider '{provider}' is not supported.")
        return client

    def generate(self, provider: str, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        """Route the generate request to the appropriate client."""
        client = self.get_client(provider)
        if not client.health():
            raise LLMError(f"Provider '{provider}' is not healthy/reachable.")
        return client.generate(model, prompt, **kwargs)
