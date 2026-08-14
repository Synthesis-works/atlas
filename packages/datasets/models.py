import uuid
from typing import Any
from pydantic import BaseModel, Field

from packages.benchmark.models.task import Task


class DatasetManifest(BaseModel):
    id: str = Field(..., description="Unique dataset identifier (e.g. humaneval)")
    name: str = Field(..., description="Human readable name")
    version: str = Field(..., description="Dataset version")
    source: str = Field(..., description="Author/Organization")
    license: str = Field(..., description="License (e.g. MIT)")
    citation: str | None = Field(None, description="Academic citation if any")
    language: str = Field(..., description="Primary language (e.g. python)")
    evaluation: str = Field(..., description="Evaluation strategy (e.g. execution)")
    metric: str = Field(..., description="Primary metric (e.g. pass@1)")
    tasks: int = Field(..., description="Expected number of tasks")
    tags: list[str] = Field(default_factory=list, description="Categorical tags")


class ImportStats(BaseModel):
    total: int = 0
    valid: int = 0
    duplicates: int = 0
    missing_metadata: int = 0
    checksum: str = ""
    languages: dict[str, int] = Field(default_factory=dict)


class DatasetPack(BaseModel):
    manifest: DatasetManifest
    tasks: list[Task] = Field(default_factory=list)
    stats: ImportStats | None = None


class TrainingExample(BaseModel):
    dataset_version_id: uuid.UUID
    task_id: uuid.UUID
    task_name: str
    prompt: str
    canonical_answer: str
    metadata: dict[str, Any] = Field(default_factory=dict)
