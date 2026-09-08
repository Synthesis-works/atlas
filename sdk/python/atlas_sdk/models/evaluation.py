"""Evaluation-parity DTOs mirroring the backend ``/api/v1`` responses.

Mirrors ``apps.backend.schemas.evaluation``, ``evaluation_cases`` and
``reports``.  Field-for-field correspondence — no renaming.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluationResultItemRead(BaseModel):
    """A single per-output evaluation result (mirror of ExecutionEvaluationResultRead)."""

    model_config = ConfigDict(protected_namespaces=())

    model_output_id: uuid.UUID
    strategy_version_id: uuid.UUID
    judge_id: uuid.UUID | None = None
    status: str
    passed: bool
    confidence: float | None = None
    reasoning: str | None = None
    raw_measurements: dict[str, Any] | None = None


class EvaluationResultsRead(BaseModel):
    """Full evaluation results for an execution (mirror of EvaluationResultsRead)."""

    execution_id: uuid.UUID
    status: str
    overall_score: float | None = None
    profile_id: uuid.UUID | None = None
    total_outputs: int
    evaluated_outputs: int
    passed_outputs: int
    results: list[EvaluationResultItemRead] = Field(default_factory=list)


class EvaluationEnqueuedRead(BaseModel):
    """Response returned by ``POST .../evaluate`` when a run is enqueued."""

    execution_id: uuid.UUID
    status: str = "QUEUED"
    message: str = "Evaluation task enqueued successfully"


class ExecutionCompareItemRead(BaseModel):
    """One leaderboard row in an execution comparison."""

    execution_id: uuid.UUID
    target_model: str | None = None
    overall_score: float | None = None
    passed_outputs: int = 0
    total_outputs: int = 0
    evaluated_outputs: int = 0
    rank: int


class ExecutionCompareResponse(BaseModel):
    """Ranked leaderboard from comparing executions."""

    leaderboard: list[ExecutionCompareItemRead] = Field(default_factory=list)


class EvaluationCaseItem(BaseModel):
    """A single evaluation-case definition to apply to a task/test case."""

    task_id: uuid.UUID
    test_case_id: uuid.UUID | None = None
    expected_answer: str | None = None
    evaluation_method: str | None = None
    accepted_answers: list[str] = Field(default_factory=list)
    rubric_criteria: dict[str, Any] | None = None


class EvaluationCaseWritten(BaseModel):
    """One test case that had evaluation-case metadata applied."""

    test_case_id: uuid.UUID
    task_id: uuid.UUID
    evaluation_method: str | None = None
    expected_answer: str | None = None


class EvaluationCaseWriteResponse(BaseModel):
    """Result of a ``create_evaluation_cases`` call."""

    dataset_id: uuid.UUID
    written: list[EvaluationCaseWritten] = Field(default_factory=list)
    skipped: int = 0


class ReportMetricRead(BaseModel):
    metric_name: str
    metric_value: float


class ReportVersionRead(BaseModel):
    id: uuid.UUID
    version_string: str
    summary: str | None = None
    execution_id: uuid.UUID | None = None
    created_at: datetime
    metrics: list[ReportMetricRead] = Field(default_factory=list)


class ReportRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
    versions: list[ReportVersionRead] = Field(default_factory=list)


class ReportListRead(BaseModel):
    project_id: uuid.UUID
    reports: list[ReportRead] = Field(default_factory=list)
    total: int = 0
