from typing import Any

from pydantic import UUID4, BaseModel


class CreateRunCommand(BaseModel):
    session_id: UUID4
    benchmark_version_id: UUID4
    adapter_version_id: UUID4
    target_model: str
    config: dict[str, Any] | None = None


class ValidateRunCommand(BaseModel):
    run_id: UUID4


class CancelRunCommand(BaseModel):
    run_id: UUID4


class PauseRunCommand(BaseModel):
    run_id: UUID4


class ResumeRunCommand(BaseModel):
    run_id: UUID4


class RetryRunCommand(BaseModel):
    run_id: UUID4
