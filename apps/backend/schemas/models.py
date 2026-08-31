"""Execution-target model catalog DTOs — ``GET /api/v1/models`` (Slice 7)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ModelStatus(StrEnum):
    """Availability of a provider/model for execution on THIS deployment.

    ``NOT_CONFIGURED`` does not mean the model id is invalid — it is a legal
    ``run submit --target-model`` value that Atlas recognizes but cannot
    currently execute (missing credentials/host).
    """

    AVAILABLE = "AVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class ModelRead(BaseModel):
    """Single execution-target model entry.

    ``id`` is the canonical string accepted by ``run submit --target-model``:
    ``mock`` (test-only) or ``provider/model``.  ``status`` mirrors the exact
    provider availability gate the execution path uses (``client.health()``).
    """

    id: str = Field(..., description="Canonical target string for run submit --target-model")
    provider: str = Field(..., description="Provider key (mock|ollama|gemini|grok|mistral|groq|nvidia)")
    display_name: str = Field(..., description="Human-friendly model label")
    status: ModelStatus = Field(
        ..., description="AVAILABLE when credentials/host are configured; NOT_CONFIGURED otherwise"
    )
    is_test_only: bool = Field(default=False, description="True for the mock test adapter")
