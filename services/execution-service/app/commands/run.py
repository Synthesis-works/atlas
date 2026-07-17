from pydantic import BaseModel, UUID4
from typing import Optional, Dict, Any

class CreateRunCommand(BaseModel):
    session_id: UUID4
    benchmark_version_id: UUID4
    adapter_version_id: UUID4
    target_model: str
    config: Optional[Dict[str, Any]] = None

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
