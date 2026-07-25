from datetime import datetime

from pydantic import BaseModel, Field

from .enums import BenchmarkCategory, Difficulty, LicenseType


class BenchmarkMetadata(BaseModel):
    benchmark_id: str = Field(..., description="Unique identifier for the benchmark")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Detailed description of the benchmark")
    author: str = Field(..., description="Author or authors of the benchmark")
    organization: str | None = Field(None, description="Organization responsible for the benchmark")
    version: str = Field(..., description="Semantic version string")
    license: LicenseType = Field(..., description="License under which the benchmark is released")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    difficulty: Difficulty = Field(..., description="Estimated difficulty level")
    estimated_runtime: int | None = Field(None, description="Estimated runtime in seconds")
    category: BenchmarkCategory = Field(..., description="Primary capability domain")
    tags: list[str] = Field(default_factory=list, description="List of relevant tags")
