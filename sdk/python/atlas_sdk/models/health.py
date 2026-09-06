"""Health / liveness / readiness DTOs.

``HealthData`` mirrors the response body of ``GET /api/v1/health`` (wrapped
inside ``APIResponse[HealthData]``).  The system probes
``GET /system/health/live`` and ``GET /system/health/ready`` return raw dicts
without the envelope, so they have their own flat models here.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthData(BaseModel):
    """Body of ``GET /health`` (inside ``APIResponse[HealthData]``)."""

    status: str
    version: str


class LivenessResponse(BaseModel):
    """Body of ``GET /api/v1/system/health/live`` — no envelope, raw dict."""

    status: str
    version: str


class ReadinessResponse(BaseModel):
    """Body of ``GET /api/v1/system/health/ready`` — no envelope, raw dict."""

    status: str
    checks: dict[str, Any] = Field(default_factory=dict)
