from pydantic import BaseModel, Field
from typing import List
from .metadata import BenchmarkMetadata
from .task import Task
from .schema import ExecutionConfig

class Benchmark(BaseModel):
    metadata: BenchmarkMetadata
    config: ExecutionConfig = Field(default_factory=ExecutionConfig)
    tasks: List[Task] = Field(default_factory=list)
