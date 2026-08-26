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


class BenchmarkVersionRead(BaseModel):
    """Single benchmark version from ``GET /api/v1/benchmarks/{id}/versions``."""

    id: uuid.UUID
    benchmark_id: uuid.UUID
    version_string: str
    state: str
    dataset_version_ids: list[uuid.UUID] | None = []
    evaluation_strategy_id: uuid.UUID | None = None


class PageResponse(BaseModel, Generic[T]):
    """Paginated response envelope from ``GET /api/v1/benchmarks``."""

    items: list[T]
    total: int
    limit: int
    offset: int | None = None
    next_cursor: str | None = None
