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
    category_ids: list[UUID] | None = []
    capability_ids: list[UUID] | None = []


class BenchmarkUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    objective: str | None = None
    category_ids: list[UUID] | None = None
    capability_ids: list[UUID] | None = None


class BenchmarkRead(BaseModel):
    id: UUID
    project_id: UUID
    state: str
    name: str

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

    class Config:
        from_attributes = True
