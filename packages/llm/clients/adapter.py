import json
import os
import random
import re
import time

from ..exceptions import LLMError
from ..models.prompt import Prompt
from ..models.response import LLMResponse
from .base import BaseLLMClient
from .gemini import GeminiClient
from .grok import GrokClient
from .groq import GroqClient
from .mistral import MistralClient
from .nvidia import NvidiaClient
from .ollama import OllamaClient


class MockClient(BaseLLMClient):
    def health(self) -> bool:
        return True

    def list_models(self) -> list:
        return ["mock-model", "mock"]

    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        time.sleep(0.05)

        match = re.search(r"def ([a-zA-Z0-9_]+)\(", prompt.user)
        func_name = match.group(1) if match else "dummy"

        r = random.random()
        if r < 0.05:
            code = "def " + func_name + "(*args, **kwargs): return True"
        elif r < 0.1:
            code = "def " + func_name + "(*args \n syntax error here"
        elif r < 0.15:
            code = "I cannot help with this."
        else:
            code = "def " + func_name + "(*args, **kwargs): return False"

        response_text = f"Here is the code:\n```python\n{code}\n```"
        return LLMResponse(  # type: ignore
            provider="mock",
            model=model,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=50,
            response=response_text,
            raw={},
            created_at=str(time.time()),
        )

    def supports_streaming(self) -> bool:
        return False

    def stream_generate(self, model: str, prompt: Prompt, **kwargs):
        raise NotImplementedError("Streaming is not supported for MockClient.")


class ProviderAdapter:
    """Routes requests from Atlas to the appropriate provider client."""

    def __init__(self):
        self.clients: dict[str, BaseLLMClient] = {
            "mock": MockClient(),
            "ollama": OllamaClient(),
            "gemini": GeminiClient(),
            "grok": GrokClient(),
            "mistral": MistralClient(),
            "groq": GroqClient(),
            "nvidia": NvidiaClient(),
        }
        self._load_providers()

    def _load_providers(self):
        config_path = os.path.join("config", "providers.json")
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    providers = json.load(f)

                if "gemini" in providers:
                    conf = providers["gemini"]
                    self.clients["gemini"] = GeminiClient(
                        base_url=conf.get(
                            "base_url", "https://generativelanguage.googleapis.com/v1beta/models"
                        ),
                        api_key_env=conf.get("api_key_env", "GEMINI_API_KEY"),
                    )

                if "grok" in providers:
                    conf = providers["grok"]
                    self.clients["grok"] = GrokClient(
                        base_url=conf.get("base_url", "https://api.x.ai/v1"),
                        api_key_env=conf.get("api_key_env", "XAI_API_KEY"),
                    )

                if "mistral" in providers:
                    conf = providers["mistral"]
                    self.clients["mistral"] = MistralClient(
                        base_url=conf.get("base_url", "https://api.mistral.ai/v1"),
                        api_key_env=conf.get("api_key_env", "MISTRAL_API_KEY"),
                    )

                if "groq" in providers:
                    conf = providers["groq"]
                    self.clients["groq"] = GroqClient(
                        base_url=conf.get("base_url", "https://api.groq.com/openai/v1"),
                        api_key_env=conf.get("api_key_env", "GROQ_API_KEY"),
                    )

                if "nvidia" in providers:
                    conf = providers["nvidia"]
                    self.clients["nvidia"] = NvidiaClient(
                        base_url=conf.get("base_url", "https://integrate.api.nvidia.com/v1"),
                        api_key_env=conf.get("api_key_env", "NVIDIA_API_KEY"),
                    )
            except Exception:
                pass

    def register_client(self, provider: str, client: BaseLLMClient):
        """Register a new provider client."""
        self.clients[provider.lower()] = client

    def resolve_provider_and_model(self, target_model: str) -> tuple[str, str]:
        """
        Determines provider name and model name from target_model string.
        Examples:
          'mock' -> ('mock', 'mock')
          'gemini-2.5-flash' -> ('gemini', 'gemini-2.5-flash')
          'google/gemini-1.5-pro' -> ('gemini', 'gemini-1.5-pro')
          'grok-2' -> ('grok', 'grok-2')
          'mistral-large-latest' -> ('mistral', 'mistral-large-latest')
          'groq/llama-3.3-70b-versatile' -> ('groq', 'llama-3.3-70b-versatile')
          'nvidia/meta/llama-3.1-405b-instruct' -> ('nvidia', 'meta/llama-3.1-405b-instruct')
          'ollama/llama3' -> ('ollama', 'llama3')
        """
        target = target_model.strip()
        lower = target.lower()

        if lower in ("mock", "mocked"):
            return "mock", "mock"

        if "/" in target:
            parts = target.split("/", 1)
            provider_prefix = parts[0].lower()
            if provider_prefix in self.clients:
                return provider_prefix, parts[1]

        if lower.startswith("gemini") or lower.startswith("google"):
            return "gemini", target
        if lower.startswith("grok") or lower.startswith("xai"):
            return "grok", target
        if lower.startswith("mistral"):
            return "mistral", target
        if lower.startswith("groq"):
            return "groq", target
        if lower.startswith("nvidia"):
            return "nvidia", target
        if lower.startswith("ollama"):
            return "ollama", target

        raise ValueError(
            f"Unsupported target model '{target_model}'. Unable to resolve to a known provider."
        )

    def get_client(self, provider: str) -> BaseLLMClient:
        client = self.clients.get(provider.lower())
        if not client:
            raise ValueError(f"Provider '{provider}' is not supported.")
        return client

    def generate(self, provider: str, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        """Route the generate request to the appropriate client."""
        client = self.get_client(provider)
        if not client.health():
            raise LLMError(
                f"Provider '{provider}' is not available. Please ensure provider API credentials/host are configured."
            )
        return client.generate(model, prompt, **kwargs)
