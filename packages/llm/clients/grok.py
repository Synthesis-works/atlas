import os
import time

import httpx

from ..exceptions import LLMError
from ..models.prompt import Prompt
from ..models.response import LLMResponse
from .base import BaseLLMClient


class GrokClient(BaseLLMClient):
    def __init__(
        self,
        base_url: str = "https://api.x.ai/v1",
        api_key_env: str = "XAI_API_KEY",
        timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.api_key = os.getenv(api_key_env)
        self.timeout = timeout

    def health(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list:
        return ["grok-2", "grok-beta"]

    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        if not self.api_key:
            raise LLMError("API key not found for Grok (xAI).")

        url = f"{self.base_url}/chat/completions"

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        temperature = kwargs.get("temperature", 0.0)
        request_timeout = kwargs.get("timeout", self.timeout)

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

        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]

        start_time = time.time()

        try:
            with httpx.Client(timeout=request_timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                raise LLMError(f"xAI API error: {response.text}")

            data = response.json()

            if "choices" not in data or not data["choices"]:
                raise LLMError("No choices returned from Grok.")

            text = data["choices"][0]["message"]["content"]

            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            return LLMResponse(  # type: ignore
                provider="grok",
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
            raise LLMError(f"Request failed: {str(e)}")

    def supports_streaming(self) -> bool:
        return False

    def stream_generate(self, model: str, prompt: Prompt, **kwargs):
        raise NotImplementedError("Streaming not implemented for Grok")
