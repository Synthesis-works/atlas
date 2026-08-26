"""Benchmark DTOs — field-for-field mirror of ``apps/backend/schemas/benchmarks.py``."""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BenchmarkRead(BaseModel):
    """Single benchmark summary from ``GET /api/v1/benchmarks``."""

    id: uuid.UUID
    project_id: uuid.UUID
    state: str
    name: str


class PageResponse(BaseModel, Generic[T]):
    """Paginated response envelope from ``GET /api/v1/benchmarks``."""

    items: list[T]
    total: int
    limit: int
    offset: int | None = None
    next_cursor: str | None = None
