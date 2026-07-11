from typing import Dict, Optional
from .base import BaseLLMClient
from .ollama import OllamaClient
from ..models.prompt import Prompt
from ..models.response import LLMResponse
from ..exceptions import LLMError

class MockClient(BaseLLMClient):
    def health(self) -> bool: return True
    def list_models(self) -> list: return []
    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        import time, random, re
        # Simulate slight delay
        time.sleep(0.5)
        
        # Extract function signature from prompt
        match = re.search(r'def ([a-zA-Z0-9_]+)\(', prompt.user)
        func_name = match.group(1) if match else "dummy"
        
        # Randomly fail with extraction error, syntax error, logic error, or pass
        r = random.random()
        if r < 0.1:
            code = "def " + func_name + "(*args, **kwargs): return True" # wrong logic
        elif r < 0.2:
            code = "def " + func_name + "(*args \n syntax error here"
        elif r < 0.3:
            code = "I cannot help with this." # refusal
        else:
            code = "def " + func_name + "(*args, **kwargs): return False" # logic error
            
        response_text = f"Here is the code:\n```python\n{code}\n```"
        return LLMResponse(
            provider="mock",
            model=model,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=500,
            response=response_text,
            raw={},
            created_at=str(time.time())
        )

    def supports_streaming(self) -> bool: return False
    def stream_generate(self, model: str, prompt: Prompt, **kwargs): pass

class ProviderAdapter:
    """Routes requests from Atlas to the appropriate provider client."""

    def __init__(self):
        self.clients: Dict[str, BaseLLMClient] = {
            "ollama": OllamaClient(),
            "mock": MockClient()
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
