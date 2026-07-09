from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ExecutionContext(BaseModel):
    language: str = Field(default="python", description="Programming language for execution")
    timeout: int = Field(default=2, description="Timeout in seconds")
    memory_limit: Optional[int] = Field(default=256, description="Memory limit in MB")
    working_directory: Optional[str] = Field(None, description="Working directory path")

class ExecutionRequest(BaseModel):
    code: str = Field(..., description="The source code to execute")
    entry_point: Optional[str] = Field(None, description="Main function or entry point")
    visible_tests: Optional[str] = Field(None, description="Visible tests provided in the prompt")
    hidden_tests: Optional[str] = Field(None, description="Hidden tests strictly for the runtime")
    context: ExecutionContext = Field(default_factory=ExecutionContext)
