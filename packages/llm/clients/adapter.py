from ..exceptions import LLMError
from ..models.prompt import Prompt
from ..models.response import LLMResponse
from .base import BaseLLMClient
from .ollama import OllamaClient


class MockClient(BaseLLMClient):
    def health(self) -> bool:
        return True

    def list_models(self) -> list:
        return []

    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        import random
        import re
        import time

        # Simulate slight delay
        time.sleep(0.5)

        # Extract function signature from prompt
        match = re.search(r"def ([a-zA-Z0-9_]+)\(", prompt.user)
        func_name = match.group(1) if match else "dummy"

        # Randomly fail with extraction error, syntax error, logic error, or pass
        r = random.random()
        if r < 0.1:
            code = "def " + func_name + "(*args, **kwargs): return True"  # wrong logic
        elif r < 0.2:
            code = "def " + func_name + "(*args \n syntax error here"
        elif r < 0.3:
            code = "I cannot help with this."  # refusal
        else:
            code = "def " + func_name + "(*args, **kwargs): return False"  # logic error

        response_text = f"Here is the code:\n```python\n{code}\n```"
        return LLMResponse(  # type: ignore
            provider="mock",
            model=model,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=500,
            response=response_text,
            raw={},
            created_at=str(time.time()),
        )

    def supports_streaming(self) -> bool:
        return False

    def stream_generate(self, model: str, prompt: Prompt, **kwargs):
        pass


class ProviderAdapter:
    """Routes requests from Atlas to the appropriate provider client."""

    def __init__(self):
        self.clients: dict[str, BaseLLMClient] = {"ollama": OllamaClient(), "mock": MockClient()}
        self._load_providers()

    def _load_providers(self):
        import json
        import os

        config_path = os.path.join("config", "providers.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                providers = json.load(f)

            if "gemini" in providers:
                from .gemini import GeminiClient

                conf = providers["gemini"]
                self.clients["gemini"] = GeminiClient(
                    base_url=conf.get(
                        "base_url", "https://generativelanguage.googleapis.com/v1beta/models"
                    ),
                    api_key_env=conf.get("api_key_env", "GEMINI_API_KEY"),
                )

            if "grok" in providers:
                from .grok import GrokClient

                conf = providers["grok"]
                self.clients["grok"] = GrokClient(
                    base_url=conf.get("base_url", "https://api.x.ai/v1"),
                    api_key_env=conf.get("api_key_env", "XAI_API_KEY"),
                )

            if "mistral" in providers:
                from .mistral import MistralClient

                conf = providers["mistral"]
                self.clients["mistral"] = MistralClient(
                    base_url=conf.get("base_url", "https://api.mistral.ai/v1"),
                    api_key_env=conf.get("api_key_env", "MISTRAL_API_KEY"),
                )

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
