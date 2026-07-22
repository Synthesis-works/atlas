from pydantic import UUID4, BaseModel


class ClaimTasksCommand(BaseModel):
    worker_id: UUID4
    max_tasks: int = 1
    # Filtering attributes (Scheduler will expand these later)
    target_model: str | None = None
    target_task_id: UUID4 | None = None


class CompleteTaskCommand(BaseModel):
    worker_id: UUID4
    task_id: UUID4
    raw_output: str
    duration_ms: int | None = None
    tokens_used: int | None = None


class FailTaskCommand(BaseModel):
    worker_id: UUID4
    task_id: UUID4
    error_code: str
    error_message: str
    retryable: bool
    stacktrace: str | None = None


class ReleaseTaskCommand(BaseModel):
    worker_id: UUID4
    task_id: UUID4
    reason: str | None = None
