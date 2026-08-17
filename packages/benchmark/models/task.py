import uuid
from typing import Any

from pydantic import BaseModel, Field

from .enums import TaskState, Visibility


class TaskConstraints(BaseModel):
    time_limit: int | None = Field(None, description="Time limit in seconds")
    memory_limit: int | None = Field(None, description="Memory limit in MB")


class EvaluationConfig(BaseModel):
    extractor: str = Field(default="noop", description="Name of the extractor plugin")
    normalizer: str = Field(default="noop", description="Name of the normalizer plugin")
    judge: str = Field(default="exact_match", description="Name of the judge plugin")
    metrics: list[str] = Field(
        default_factory=lambda: ["accuracy"], description="List of metric plugins"
    )
    kwargs: dict[str, Any] = Field(default_factory=dict, description="Additional args for plugins")


class Task(BaseModel):
    state: TaskState = Field(default=TaskState.IMPORTED, description="Current state of the task")
    task_id: str = Field(..., description="Unique identifier for the task")
    dataset_version_id: uuid.UUID | None = Field(
        None, description="Associated dataset version, if part of a dataset"
    )
    title: str = Field(..., description="Title of the task")
    description: str = Field(..., description="Description of the task")
    input: Any = Field(..., description="Input data or prompt for the model")
    expected_output: Any = Field(..., description="Expected output for evaluation")
    hidden_tests: Any | None = Field(None, description="Hidden tests to evaluate the model")
    constraints: TaskConstraints = Field(default_factory=TaskConstraints)  # type: ignore
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    visibility: Visibility = Field(default=Visibility.PUBLIC)
    metadata: dict[str, Any] = Field(default_factory=dict)
