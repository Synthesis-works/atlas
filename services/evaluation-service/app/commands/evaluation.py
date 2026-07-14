from pydantic import BaseModel, UUID4
from typing import Optional

class CreateEvaluationJobCommand(BaseModel):
    atlas_run_id: UUID4

class StartEvaluationAttemptCommand(BaseModel):
    job_id: UUID4
    pipeline_version_id: UUID4

from app.pipelines.base import EvaluationResultBundle

class CompleteEvaluationAttemptCommand(BaseModel):
    attempt_id: UUID4
    result_bundle: EvaluationResultBundle

class FailEvaluationAttemptCommand(BaseModel):
    attempt_id: UUID4
    error_message: Optional[str] = None

class CancelEvaluationJobCommand(BaseModel):
    job_id: UUID4
