import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Benchmark Versions
# -----------------------------------------------------------------------------

class BenchmarkVersionCreate(BaseModel):
    version_string: str = Field(..., max_length=50)
    primary_dataset_version_id: Optional[uuid.UUID] = None
    evaluation_config: Optional[Dict[str, Any]] = None
    metric_config: Optional[Dict[str, Any]] = None
    scoring_policy: Optional[Dict[str, Any]] = None

class BenchmarkVersionRead(BaseModel):
    id: uuid.UUID
    benchmark_id: uuid.UUID
    version_string: str
    primary_dataset_version_id: Optional[uuid.UUID]
    evaluation_config: Optional[Dict[str, Any]]
    metric_config: Optional[Dict[str, Any]]
    scoring_policy: Optional[Dict[str, Any]]
    created_at: datetime
    created_by_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}

# -----------------------------------------------------------------------------
# Benchmarks
# -----------------------------------------------------------------------------

class BenchmarkCreate(BaseModel):
    name: str = Field(..., max_length=255)
    objective: Optional[str] = None
    difficulty: Optional[str] = Field(None, max_length=50)
    domain: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50)
    visibility: Optional[str] = Field(None, max_length=50)
    
    # Creation of a benchmark requires its first version configuration
    initial_version: BenchmarkVersionCreate

class BenchmarkRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    objective: Optional[str]
    difficulty: Optional[str]
    domain: Optional[str]
    type: Optional[str]
    visibility: Optional[str]
    author_id: Optional[uuid.UUID]
    status: Optional[str]
    
    versions: List[BenchmarkVersionRead] = []

    model_config = {"from_attributes": True}
