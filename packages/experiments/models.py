from pydantic import BaseModel, Field
from typing import Optional

class ExperimentConfig(BaseModel):
    dataset: str = Field(..., description="Dataset or benchmark pack name (e.g. HumanEval)")
    provider: str = Field(default="ollama", description="LLM provider name")
    model: str = Field(..., description="The model being evaluated")
    prompt_version: str = Field(default="v1", description="Prompt version to use")
    max_tasks: Optional[int] = Field(default=None, description="Max number of tasks to run")
    shuffle: bool = Field(default=False, description="Whether to shuffle the tasks")
    temperature: float = Field(default=0.0, description="Sampling temperature")
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
