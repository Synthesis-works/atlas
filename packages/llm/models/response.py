from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class LLMResponse(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the response")
    provider: str = Field(..., description="Provider name (e.g., ollama, openai)")
    model: str = Field(..., description="Model name used for generation")
    prompt_tokens: Optional[int] = Field(None, description="Number of tokens in the prompt")
    completion_tokens: Optional[int] = Field(None, description="Number of tokens in the completion")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    latency_ms: int = Field(..., description="Latency of the generation in milliseconds")
    response: str = Field(..., description="Generated text response")
    raw: Optional[Dict[str, Any]] = Field(None, description="Raw response payload from the provider")
    created_at: str = Field(..., description="Timestamp of the response creation")
