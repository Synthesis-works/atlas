import os
import time

import httpx

from ..exceptions import LLMError
from ..models.prompt import Prompt
from ..models.response import LLMResponse
from .base import BaseLLMClient


class GeminiClient(BaseLLMClient):
    def __init__(
        self,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta/models",
        api_key_env: str = "GEMINI_API_KEY",
    ):
        self.base_url = base_url
        self.api_key = os.getenv(api_key_env)

    def health(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list:
        return ["gemini-2.5-flash", "gemini-1.5-pro"]

    def generate(self, model: str, prompt: Prompt, **kwargs) -> LLMResponse:
        if not self.api_key:
            raise LLMError("API key not found for Gemini.")

        url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"

        headers = {"Content-Type": "application/json"}

        # Determine temperature from kwargs
        temperature = kwargs.get("temperature", 0.0)

        # Build contents
        contents = []
        if prompt.system:
            # Gemini typically handles system instructions in a separate field
            system_instruction = {"parts": [{"text": prompt.system}]}
        else:
            system_instruction = None

        contents.append({"role": "user", "parts": [{"text": prompt.user}]})

        payload = {"contents": contents, "generationConfig": {"temperature": temperature}}

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        start_time = time.time()

        try:
            # Gemini might take a few seconds
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=payload)

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                raise LLMError(f"Gemini API error: {response.text}")

            data = response.json()

            if "candidates" not in data or not data["candidates"]:
                raise LLMError("No candidates returned from Gemini.")

            text = data["candidates"][0]["content"]["parts"][0]["text"]

            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)
            total_tokens = usage.get("totalTokenCount", 0)

            return LLMResponse(
                provider="gemini",
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
        raise NotImplementedError("Streaming not implemented for Gemini")
