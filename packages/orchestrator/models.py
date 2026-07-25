from enum import Enum

from pydantic import BaseModel, Field


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
    git_commit: str | None = Field(default=None, description="Git commit hash")
    python_version: str | None = Field(default=None, description="Python version")
    ollama_version: str | None = Field(default=None, description="Ollama version")
    model_digest: str | None = Field(default=None, description="Model manifest digest")
    os_info: str | None = Field(default=None, description="Operating system")
    cpu_info: str | None = Field(default=None, description="CPU info")
    ram_gb: float | None = Field(default=None, description="Total RAM in GB")
    atlas_version: str = Field(default="0.9.0", description="Atlas version")
    parent_experiment: str | None = Field(default=None, description="Parent experiment ID")
    lineage_change: str | None = Field(default=None, description="What changed vs parent")
    lineage_reason: str | None = Field(default=None, description="Reason for change")


class TaskRunResult(BaseModel):
    task_id: str = Field(..., description="Task identifier")
    state: TaskRunState = Field(default=TaskRunState.QUEUED, description="Current execution state")

    # Generation Stage
    prompt: str | None = None
    raw_response: str | None = None
    extracted_code: str | None = None
    generation_latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    # Tracking
    model: str | None = None
    prompt_version: str | None = None
    runtime: str | None = None

    tokens: int | None = None
    status: str | None = Field(default=None)
    tests_passed: bool = Field(default=False)

    # Execution Stage
    execution_status: str | None = None
    execution_latency_ms: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    exception: str | None = None

    # Evaluation Stage
    evaluation_status: str | None = None  # PASS, FAIL, ERROR
    score: float | None = None
    confidence: float | None = None

    # Overall
    error_message: str | None = None
