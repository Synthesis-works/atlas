import uuid
from typing import Any

from pydantic import BaseModel, Field


class EvaluationCaseItem(BaseModel):
    task_id: uuid.UUID
    test_case_id: uuid.UUID | None = None
    expected_answer: str | None = None
    evaluation_method: str | None = None
    accepted_answers: list[str] = Field(default_factory=list)
    rubric_criteria: dict[str, Any] | None = None


class EvaluationCaseCreate(BaseModel):
    evaluation_cases: list[EvaluationCaseItem] = Field(min_length=1)


class EvaluationCaseWritten(BaseModel):
    test_case_id: uuid.UUID
    task_id: uuid.UUID
    evaluation_method: str | None = None
    expected_answer: str | None = None

    model_config = {"from_attributes": True}


class EvaluationCaseWriteResponse(BaseModel):
    dataset_id: uuid.UUID
    written: list[EvaluationCaseWritten] = Field(default_factory=list)
    skipped: int = 0
