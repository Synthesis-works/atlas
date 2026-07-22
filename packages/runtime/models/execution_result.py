from enum import Enum

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    SECURITY_VIOLATION = "security_violation"
    IMPORT_ERROR = "import_error"
    UNKNOWN = "unknown"


class ExecutionResult(BaseModel):
    execution_id: str = Field(..., description="Unique identifier for this execution")
    status: ExecutionStatus = Field(..., description="The final status of the execution")
    stdout: str = Field(default="", description="Standard output from the run")
    stderr: str = Field(default="", description="Standard error from the run")
    exit_code: int | None = Field(None, description="Process exit code")
    runtime_ms: int = Field(default=0, description="Execution time in milliseconds")
    timed_out: bool = Field(default=False, description="Whether the process timed out")
    memory_used: int | None = Field(None, description="Memory used during execution in MB")
    passed: bool = Field(default=False, description="Whether the execution passed all tests")
    failed: bool = Field(default=False, description="Whether the execution failed any tests")
    exception: str | None = Field(
        None, description="String representation of any internal exception"
    )
