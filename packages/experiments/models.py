from pydantic import BaseModel, Field


class ExperimentConfig(BaseModel):
    dataset: str = Field(..., description="Dataset or benchmark pack name (e.g. HumanEval)")
    provider: str = Field(default="ollama", description="LLM provider name")
    model: str = Field(..., description="The model being evaluated")
    prompt_version: str = Field(default="v1", description="Prompt version to use")
    max_tasks: int | None = Field(default=None, description="Max number of tasks to run")
    shuffle: bool = Field(default=False, description="Whether to shuffle the tasks")
    temperature: float = Field(default=0.0, description="Sampling temperature")
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
