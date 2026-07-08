from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from .enums import Visibility

class TaskConstraints(BaseModel):
    time_limit: Optional[int] = Field(None, description="Time limit in seconds")
    memory_limit: Optional[int] = Field(None, description="Memory limit in MB")

class Task(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task")
    title: str = Field(..., description="Title of the task")
    description: str = Field(..., description="Description of the task")
    input: Any = Field(..., description="Input data or prompt for the model")
    expected_output: Any = Field(..., description="Expected output for evaluation")
    hidden_tests: Optional[Any] = Field(None, description="Hidden tests to evaluate the model")
    constraints: TaskConstraints = Field(default_factory=TaskConstraints)
    visibility: Visibility = Field(default=Visibility.PUBLIC)
    metadata: Dict[str, Any] = Field(default_factory=dict)
