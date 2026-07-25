from pydantic import BaseModel, Field


class ExecutionContext(BaseModel):
    language: str = Field(default="python", description="Programming language for execution")
    timeout: int = Field(default=2, description="Timeout in seconds")
    memory_limit: int | None = Field(default=256, description="Memory limit in MB")
    working_directory: str | None = Field(None, description="Working directory path")


class ExecutionRequest(BaseModel):
    code: str = Field(..., description="The source code to execute")
    entry_point: str | None = Field(None, description="Main function or entry point")
    visible_tests: str | None = Field(None, description="Visible tests provided in the prompt")
    hidden_tests: str | None = Field(None, description="Hidden tests strictly for the runtime")
    context: ExecutionContext = Field(default_factory=ExecutionContext)  # type: ignore
