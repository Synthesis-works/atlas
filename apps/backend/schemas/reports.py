import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    benchmark_id: uuid.UUID | None = None
    execution_id: uuid.UUID | None = None
    version_string: str | None = None


class ReportMetricRead(BaseModel):
    metric_name: str
    metric_value: float

    model_config = {"from_attributes": True}


class ReportVersionRead(BaseModel):
    id: uuid.UUID
    version_string: str
    summary: str | None = None
    execution_id: uuid.UUID | None = None
    created_at: datetime
    metrics: list[ReportMetricRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ReportRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
    versions: list[ReportVersionRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ReportListRead(BaseModel):
    project_id: uuid.UUID
    reports: list[ReportRead] = Field(default_factory=list)
    total: int = 0
