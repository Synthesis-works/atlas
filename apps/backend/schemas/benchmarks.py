from uuid import UUID

from pydantic import BaseModel, Field


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
