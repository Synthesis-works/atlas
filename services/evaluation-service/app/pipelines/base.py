from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MetricValueModel(BaseModel):
    name: str
    value: float
    category: str
    direction: str
    unit: str
    source: str
    aggregation: str
    normalized_value: float | None = None
    confidence: float | None = None
    metadata: dict[str, Any] | None = None


class ArtifactModel(BaseModel):
    artifact_hash: str
    target_output: dict[str, Any]
    reference_data: dict[str, Any] | None = None
    context: dict[str, Any] | None = None


class JudgeTraceModel(BaseModel):
    prompt: str
    response: str
    rubric: str
    reasoning: str
    latency_ms: float | None = None
    cost: float | None = None
    metadata: dict[str, Any] | None = None


class EvaluationResultBundle(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metrics: list[MetricValueModel] = []
    artifacts: list[ArtifactModel] = []
    judge_traces: list[JudgeTraceModel] = []
    warnings: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class PipelineContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    evaluation_attempt_id: UUID
    execution_outputs: list[dict[str, Any]]
    benchmark: dict[str, Any]
    dataset: dict[str, Any] | None = None
    configuration: dict[str, Any]
    artifacts: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}


class EvaluationPipeline(Protocol):
    def evaluate(self, context: PipelineContext) -> EvaluationResultBundle:
        """Executes the evaluation pipeline against the provided context."""
        ...
