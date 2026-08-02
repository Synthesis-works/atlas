from pydantic import BaseModel, Field

from .metadata import BenchmarkMetadata
from .schema import ExecutionConfig
from .task import Task


class Benchmark(BaseModel):
    metadata: BenchmarkMetadata
    config: ExecutionConfig = Field(default_factory=ExecutionConfig)  # type: ignore
    tasks: list[Task] = Field(default_factory=list)
