import time

import httpx

from ..config import OLLAMA_HOST
from ..exceptions import GenerationError, LLMConnectionError, ModelNotFoundError, TimeoutError
from ..models.prompt import Prompt
from ..models.response import LLMResponse
from ..models.model_types import ModelInfo
from .base import BaseLLMClient


class OllamaClient(BaseLLMClient):
    """Ollama client communicating via HTTP REST API."""

    def __init__(self, host: str = OLLAMA_HOST):
        self.host = host.rstrip("/")

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(self.host)
                return response.status_code == 200  # type: ignore
        except Exception:
            return False

    def list_models(self) -> list[ModelInfo]:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.host}/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for m in data.get("models", []):
                    details = m.get("details", {})
                    models.append(
                        ModelInfo(
                            name=m.get("name", ""),
                            size=m.get("size", 0),
                            family=details.get("family", ""),
                            parameter_size=details.get("parameter_size", ""),
                            quantization=details.get("quantization_level", ""),
                        )
                    )
                return models
        except httpx.RequestError as e:
            raise LLMConnectionError(f"Failed to connect to Ollama at {self.host}: {e}")

    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        start_time = time.time()

        # Build the prompt string. For simple completion, we combine system and user.
        full_prompt = f"{prompt.system}\n\n{prompt.user}" if prompt.system else prompt.user

        payload = {"model": model, "prompt": full_prompt, "stream": False, **kwargs}

        try:
            # We use a longer timeout for generation
            with httpx.Client(timeout=120.0) as client:
                response = client.post(f"{self.host}/api/generate", json=payload)

                if response.status_code == 404:
                    raise ModelNotFoundError(f"Model {model} not found in Ollama.")
                response.raise_for_status()

                data = response.json()
                latency_ms = int((time.time() - start_time) * 1000)

                return LLMResponse(
                    provider="ollama",
                    model=model,
                    prompt_tokens=data.get("prompt_eval_count"),
                    completion_tokens=data.get("eval_count"),
                    total_tokens=(data.get("prompt_eval_count") or 0)
                    + (data.get("eval_count") or 0),
                    latency_ms=latency_ms,
                    response=data.get("response", ""),
                    raw=data,
                    created_at=data.get("created_at", ""),
                )
        except httpx.TimeoutException:
            raise TimeoutError("Generation timed out after 120 seconds.")
        except httpx.RequestError as e:
            raise LLMConnectionError(f"Failed to communicate with Ollama: {e}")
        except Exception as e:
            raise GenerationError(f"Failed to generate response: {e}")

    def supports_streaming(self) -> bool:
        return True

    def stream_generate(self, model: str, prompt: Prompt, **kwargs):
        """Stream a completion for the given prompt."""
        raise NotImplementedError("Streaming is not yet supported for OllamaClient.")
