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


class CapabilityScoreRead(BaseModel):
    """Capability score breakdown entry.

    Mirrors ``CapabilityScoreRead`` from the backend.
    """

    capability_name: str
    score: float


class ReportSummaryRead(BaseModel):
    """Detailed report summary for a single execution run.

    Mirrors ``ReportSummaryRead`` from the backend.
    Note: ``GET /api/v1/reports/runs/{run_id}`` returns this directly (not
    wrapped in ``APIResponse``).
    """

    run_id: uuid.UUID
    benchmark_id: uuid.UUID
    benchmark_name: str
    benchmark_version: str
    target_model: str
    evaluation_status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    overall_score: float | None = None
    scores: list[CapabilityScoreRead] = []


class PaginatedReportRunsRead(BaseModel):
    """Paginated list of report run entries.

    Mirrors ``PaginatedReportRunsRead`` from the backend.
    Note: the response uses ``page``/``size``, not ``offset``/``limit``.
    """

    items: list[ReportRunEntryRead]
    total: int
    page: int
    size: int


class DownloadResult(BaseModel):
    """Raw bytes from a download endpoint plus response metadata.

    Not a mirror of a backend JSON schema — this is a client-side artifact
    returned by ``AtlasClient.export_report_run()``.

    ``filename`` is parsed from the ``Content-Disposition`` header (when
    present) or falls back to ``report-<run_id>.<ext>``.  ``content_type``
    is the response ``Content-Type`` header, if any.
    """

    content: bytes
    filename: str
    content_type: str | None = None
