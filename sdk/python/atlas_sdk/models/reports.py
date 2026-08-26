"""Report DTOs — field-for-field mirror of report API responses.

Mirrors ``GET /api/v1/reports/runs`` response schemas from
``apps/backend/schemas/reporting.py``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ReportRunStatus(StrEnum):
    """Evaluation status of a report run (mirrors backend ReportRunStatus)."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ReportRunEntryRead(BaseModel):
    """Single report run entry in a paginated list.

    Mirrors ``ReportRunEntryRead`` from the backend.
    """

    run_id: uuid.UUID
    benchmark_id: uuid.UUID
    benchmark_version: str
    target_model: str
    evaluation_status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    overall_score: float | None = None


class PaginatedReportRunsRead(BaseModel):
    """Paginated list of report run entries.

    Mirrors ``PaginatedReportRunsRead`` from the backend.
    Note: the response uses ``page``/``size``, not ``offset``/``limit``.
    """

    items: list[ReportRunEntryRead]
    total: int
    page: int
    size: int
