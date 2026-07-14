from pydantic import BaseModel, UUID4
from typing import Optional, Dict, Any, List
from datetime import datetime

class ClaimTasksCommand(BaseModel):
    worker_id: UUID4
    max_tasks: int = 1
    # Filtering attributes (Scheduler will expand these later)
    target_model: Optional[str] = None
    target_task_id: Optional[UUID4] = None

class CompleteTaskCommand(BaseModel):
    worker_id: UUID4
    task_id: UUID4
    raw_output: str
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None

class FailTaskCommand(BaseModel):
    worker_id: UUID4
    task_id: UUID4
    error_code: str
    error_message: str
    retryable: bool
    stacktrace: Optional[str] = None

class ReleaseTaskCommand(BaseModel):
    worker_id: UUID4
    task_id: UUID4
    reason: Optional[str] = None
