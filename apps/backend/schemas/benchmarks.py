from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from apps.backend.schemas.query import BaseFilterRequest
from atlas_db.models.authoring import BenchmarkState
from fastapi import Query


class BenchmarkSortField(str, Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NAME = "name"


class BenchmarkFilterRequest(BaseFilterRequest):
    category_ids: list[UUID] | None = Query(None, description="Filter by category IDs")
    capability_ids: list[UUID] | None = Query(None, description="Filter by capability IDs")
    owner_id: UUID | None = Field(None, description="Filter by owner ID")
    status: BenchmarkState | None = Field(None, description="Filter by benchmark status")


class BenchmarkCreate(BaseModel):
    name: str = Field(..., max_length=255)
    objective: str | None = None
    domain: str | None = None
    difficulty: str | None = None
    type: str | None = None
    category_ids: list[UUID] | None = []
    capability_ids: list[UUID] | None = []


class BenchmarkUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    objective: str | None = None
    domain: str | None = None
    difficulty: str | None = None
    type: str | None = None
    category_ids: list[UUID] | None = None
    capability_ids: list[UUID] | None = None


class BenchmarkRead(BaseModel):
    id: UUID
    project_id: UUID
    state: str
    name: str
    objective: str | None = None
    domain: str | None = None
    difficulty: str | None = None
    type: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    versions: list[BenchmarkVersionRead] = []

    # Real persisted telemetry fields (null when no execution/evaluation history exists)
    primary_dataset_id: UUID | None = None
    primary_dataset_version_id: UUID | None = None
    evaluation_case_count: int | None = None
    execution_count: int | None = None
    completed_execution_count: int | None = None
    failed_execution_count: int | None = None
    evaluation_count: int | None = None
    passed_evaluation_count: int | None = None
    average_score: float | None = None
    latest_score: float | None = None
    latest_execution_at: datetime | None = None
    average_latency_ms: float | None = None

    class Config:
        from_attributes = True


class BenchmarkVersionCreate(BaseModel):
    version_string: str
    dataset_version_ids: list[UUID] | None = []
    evaluation_strategy_id: UUID | None = None


class BenchmarkVersionUpdate(BaseModel):
    dataset_version_ids: list[UUID] | None = None
    evaluation_strategy_id: UUID | None = None


class BenchmarkVersionRead(BaseModel):
    id: UUID
    benchmark_id: UUID
    version_string: str
    state: str
    dataset_version_ids: list[UUID] | None = []
    evaluation_strategy_id: UUID | None = None
    evaluation_case_count: int | None = None
    execution_count: int | None = None
    average_score: float | None = None
    latest_score: float | None = None

    class Config:
        from_attributes = True

