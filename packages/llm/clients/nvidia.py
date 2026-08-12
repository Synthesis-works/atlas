import os
import time
import httpx

from ..exceptions import LLMError
from ..models.prompt import Prompt
from ..models.response import LLMResponse
from ..models.model_types import ModelInfo
from .base import BaseLLMClient


class NvidiaClient(BaseLLMClient):
    """
    Client for NVIDIA NIM API (OpenAI-compatible chat completions endpoint).
    """

    def __init__(
        self,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        api_key_env: str = "NVIDIA_API_KEY",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = os.getenv(api_key_env)

    def health(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                name=m,
                size=0,
                family="nvidia",
                parameter_size="unknown",
                quantization="none",
            )
            for m in [
                "meta/llama-3.1-405b-instruct",
                "meta/llama-3.1-70b-instruct",
                "nvidia/neva-22b",
            ]
        ]

    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        if not self.api_key:
            raise LLMError("API key not found for NVIDIA NIM (NVIDIA_API_KEY).")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        temperature = kwargs.get("temperature", 0.0)
        messages = []
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})
        messages.append({"role": "user", "content": prompt.user})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        start_time = time.time()
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=payload)

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                raise LLMError(f"NVIDIA API error ({response.status_code}): {response.text}")

            data = response.json()
            if "choices" not in data or not data["choices"]:
                raise LLMError("No choices returned from NVIDIA API.")

            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            return LLMResponse(  # type: ignore
                provider="nvidia",
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                response=text,
                raw=data,
                created_at=str(time.time()),
            )
        except httpx.RequestError as e:
            raise LLMError(f"Request to NVIDIA API failed: {str(e)}")

    def supports_streaming(self) -> bool:
        return False

    def stream_generate(self, model: str, prompt: Prompt, **kwargs):
        raise NotImplementedError("Streaming is not yet supported for NVIDIA.")
