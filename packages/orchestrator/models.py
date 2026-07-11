from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class TaskRunState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    GENERATED = "generated"
    EXECUTED = "executed"
    EVALUATED = "evaluated"
    FAILED = "failed"
    SKIPPED = "skipped"

class JobConfig(BaseModel):
    job_id: str = Field(..., description="Unique ID for the job")
    benchmark_pack: str = Field(..., description="The name of the benchmark pack")
    model: str = Field(..., description="The model being evaluated")
    provider: str = Field(..., description="The provider hosting the model")
    prompt_version: str = Field(default="v1", description="The prompt version being used")
    seed: int = Field(default=42, description="Random seed for reproducibility")
    git_commit: Optional[str] = Field(default=None, description="Git commit hash")
    python_version: Optional[str] = Field(default=None, description="Python version")
    ollama_version: Optional[str] = Field(default=None, description="Ollama version")
    model_digest: Optional[str] = Field(default=None, description="Model manifest digest")
    os_info: Optional[str] = Field(default=None, description="Operating system")
    cpu_info: Optional[str] = Field(default=None, description="CPU info")
    ram_gb: Optional[float] = Field(default=None, description="Total RAM in GB")
    atlas_version: str = Field(default="0.9.0", description="Atlas version")
    parent_experiment: Optional[str] = Field(default=None, description="Parent experiment ID")
    lineage_change: Optional[str] = Field(default=None, description="What changed vs parent")
    lineage_reason: Optional[str] = Field(default=None, description="Reason for change")
class TaskRunResult(BaseModel):
    task_id: str = Field(..., description="Task identifier")
    state: TaskRunState = Field(default=TaskRunState.QUEUED, description="Current execution state")
    
    # Generation Stage
    prompt: Optional[str] = None
    raw_response: Optional[str] = None
    extracted_code: Optional[str] = None
    generation_latency_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    
    # Tracking
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    runtime: Optional[str] = None
    
    tokens: Optional[int] = None
    status: Optional[str] = Field(default=None)
    tests_passed: bool = Field(default=False)
    
    # Execution Stage
    execution_status: Optional[str] = None
    execution_latency_ms: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exception: Optional[str] = None
    
    # Evaluation Stage
    evaluation_status: Optional[str] = None  # PASS, FAIL, ERROR
    score: Optional[float] = None
    confidence: Optional[float] = None
    
    # Overall
    error_message: Optional[str] = None
