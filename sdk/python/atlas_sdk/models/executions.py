"""Execution DTOs — field-for-field mirror of execution API responses.

The execution endpoints return ``ExecutionResponse`` directly (not wrapped in
``APIResponse``), unlike most other Atlas endpoints.  Error responses still
follow the standard ``APIResponse`` error envelope via FastAPI's exception
handler.

Status lifecycle::

    QUEUED -> SCHEDULED -> STARTING -> RUNNING -> EVALUATING -> COMPLETED
                                   |-> FAILED / RETRYING
                                   |-> CANCELLING -> CANCELLED
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ExecutionState(StrEnum):
    """Execution lifecycle state (mirrors domain ExecutionState)."""

    QUEUED = "QUEUED"
    SCHEDULED = "SCHEDULED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"


class ArtifactResponse(BaseModel):
    """Single artifact attached to an execution attempt."""

    id: uuid.UUID
    type: str
    storage_uri: str


class ExecutionAttemptResponse(BaseModel):
    """Details of a single execution attempt."""

    id: uuid.UUID
    run_id: uuid.UUID
    task_id: uuid.UUID
    worker_id: uuid.UUID | None = None
    status: str
    target_model: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    artifacts: list[ArtifactResponse] = []


class ExecutionResponse(BaseModel):
    """Full execution record returned by submit / get / list / cancel.

    Not wrapped in ``APIResponse`` — the endpoint returns this directly.
    """

    id: uuid.UUID
    benchmark_version_id: uuid.UUID
    status: str  # ExecutionState value as string
    target_model: str = "gemini-2.5-flash"
    completed_items: int = 0
    total_items: int = 1
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID
    max_retries: int = 3
    attempts: list[ExecutionAttemptResponse] = []


class ExecutionCreateRequest(BaseModel):
    """Request body for ``POST /api/v1/benchmarks/{bv_id}/executions``."""

    target_model: str = "gemini-2.5-flash"
    dataset_version_id: uuid.UUID | None = None
    execution_config: dict[str, Any] | None = None
