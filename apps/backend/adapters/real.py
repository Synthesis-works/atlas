import logging
import time
from typing import Any

import httpx

from packages.llm.clients.adapter import ProviderAdapter
from packages.llm.exceptions import LLMError
from packages.llm.models.prompt import Prompt
from .base import BaseModelAdapter, PredictionResult

logger = logging.getLogger(__name__)


class RealModelAdapter(BaseModelAdapter):
    """
    Adapter that routes execution predictions through real LLM provider clients.
    """

    def __init__(self, target_model: str, max_retries: int = 2, backoff_factor: float = 1.0):
        self.target_model = target_model
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.provider_adapter = ProviderAdapter()

    def predict(self, prompt_text: str) -> PredictionResult:
        try:
            provider, model = self.provider_adapter.resolve_provider_and_model(self.target_model)
        except ValueError as e:
            raise LLMError(f"Configuration error for model '{self.target_model}': {str(e)}")

        client = self.provider_adapter.get_client(provider)
        if not client.health():
            raise LLMError(
                f"Provider '{provider}' is unavailable: API key or endpoint host is not configured."
            )

        prompt = Prompt(user=prompt_text)
        attempt = 0
        last_exception: Exception | None = None

        while attempt <= self.max_retries:
            try:
                response = client.generate(model, prompt)
                return PredictionResult(
                    output_text=response.response,
                    latency_ms=response.latency_ms,
                    token_usage=response.total_tokens,
                    raw_response=response.raw,
                )
            except LLMError as e:
                # Do not retry auth errors or missing keys
                error_msg = str(e)
                if "API key" in error_msg or "401" in error_msg or "403" in error_msg or "not found" in error_msg:
                    raise

                last_exception = e
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} for target '{self.target_model}' failed with transient error: {e}. Retrying in {sleep_time}s..."
                    )
                    time.sleep(sleep_time)
                attempt += 1
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} for target '{self.target_model}' failed: {e}. Retrying in {sleep_time}s..."
                    )
                    time.sleep(sleep_time)
                attempt += 1

        raise LLMError(
            f"Execution failed for model '{self.target_model}' after {self.max_retries + 1} attempts: {last_exception}"
        )
