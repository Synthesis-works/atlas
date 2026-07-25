from typing import Any

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    id: str | None = Field(None, description="Unique identifier for the response")
    provider: str = Field(..., description="Provider name (e.g., ollama, openai)")
    model: str = Field(..., description="Model name used for generation")
    prompt_tokens: int | None = Field(None, description="Number of tokens in the prompt")
    completion_tokens: int | None = Field(None, description="Number of tokens in the completion")
    total_tokens: int | None = Field(None, description="Total tokens used")
    latency_ms: int = Field(..., description="Latency of the generation in milliseconds")
    response: str = Field(..., description="Generated text response")
    raw: dict[str, Any] | None = Field(None, description="Raw response payload from the provider")
    created_at: str = Field(..., description="Timestamp of the response creation")
