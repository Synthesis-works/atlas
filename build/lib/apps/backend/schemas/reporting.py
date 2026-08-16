import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from services.report.models.read_models import ReportRunStatus


class CapabilityScoreRead(BaseModel):
    capability_name: str = Field(
        ..., description="Name of the evaluated capability (e.g., reasoning, coding)"
    )
    score: float = Field(..., description="Normalized score for this capability (0.0 to 100.0)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "capability_name": "reasoning",
                "score": 92.5,
            }
        },
    )


class CapabilityDashboardRead(BaseModel):
    model_identifier: str = Field(..., description="Unique model identifier or name (e.g., gpt-4o)")
    overall_score: float = Field(
        ..., description="Aggregated overall score across all capabilities"
    )
    scores: list[CapabilityScoreRead] = Field(
        default_factory=list, description="Breakdown of capability scores"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "model_identifier": "gpt-4o",
                "overall_score": 88.5,
                "scores": [
                    {"capability_name": "reasoning", "score": 92.0},
                    {"capability_name": "code_generation", "score": 85.0},
                ],
            }
        },
    )


class ReportSummaryRead(BaseModel):
    run_id: uuid.UUID = Field(..., description="Unique ID of the execution run")
    benchmark_id: uuid.UUID = Field(..., description="Unique ID of the parent benchmark")
    benchmark_name: str = Field(..., description="Name of the benchmark")
    benchmark_version: str = Field(..., description="Version string of the benchmark executed")
    target_model: str = Field(..., description="Target model evaluated in this run")
    evaluation_status: ReportRunStatus = Field(
        ..., description="Current evaluation status of the run"
    )
    started_at: datetime | None = Field(None, description="Timestamp when execution started")
    completed_at: datetime | None = Field(None, description="Timestamp when execution completed")
    overall_score: float | None = Field(None, description="Overall evaluated score if completed")
    scores: list[CapabilityScoreRead] = Field(
        default_factory=list, description="Detailed capability score breakdown"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "run_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "benchmark_id": "7fa85f64-5717-4562-b3fc-2c963f66afa0",
                "benchmark_name": "HumanEval",
                "benchmark_version": "1.0.0",
                "target_model": "gpt-4o",
                "evaluation_status": "COMPLETED",
                "started_at": "2026-07-27T10:00:00Z",
                "completed_at": "2026-07-27T10:05:00Z",
                "overall_score": 88.5,
                "scores": [
                    {"capability_name": "reasoning", "score": 92.0},
                    {"capability_name": "code_generation", "score": 85.0},
                ],
            }
        },
    )


class ReportRunEntryRead(BaseModel):
    run_id: uuid.UUID = Field(..., description="Unique ID of the execution run")
    benchmark_id: uuid.UUID = Field(..., description="Unique ID of the benchmark")
    benchmark_version: str = Field(..., description="Version string of the benchmark executed")
    target_model: str = Field(..., description="Target model evaluated in this run")
    evaluation_status: ReportRunStatus = Field(
        ..., description="Current evaluation status of the run"
    )
    started_at: datetime | None = Field(None, description="Timestamp when execution started")
    completed_at: datetime | None = Field(None, description="Timestamp when execution completed")
    overall_score: float | None = Field(None, description="Overall evaluated score if completed")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "run_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "benchmark_id": "7fa85f64-5717-4562-b3fc-2c963f66afa0",
                "benchmark_version": "1.0.0",
                "target_model": "gpt-4o",
                "evaluation_status": "COMPLETED",
                "started_at": "2026-07-27T10:00:00Z",
                "completed_at": "2026-07-27T10:05:00Z",
                "overall_score": 88.5,
            }
        },
    )


class PaginatedReportRunsRead(BaseModel):
    items: list[ReportRunEntryRead] = Field(..., description="List of report run summaries")
    total: int = Field(..., description="Total number of matching execution runs")
    page: int = Field(..., description="Current page number (1-indexed)")
    size: int = Field(..., description="Number of items per page")

    model_config = ConfigDict(from_attributes=True)
