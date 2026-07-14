from typing import Protocol, Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID

class MetricValueModel(BaseModel):
    name: str
    value: float
    category: str
    direction: str
    unit: str
    source: str
    aggregation: str
    normalized_value: Optional[float] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class ArtifactModel(BaseModel):
    artifact_hash: str
    target_output: Dict[str, Any]
    reference_data: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None

class JudgeTraceModel(BaseModel):
    prompt: str
    response: str
    rubric: str
    reasoning: str
    latency_ms: Optional[float] = None
    cost: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class EvaluationResultBundle(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    metrics: List[MetricValueModel] = []
    artifacts: List[ArtifactModel] = []
    judge_traces: List[JudgeTraceModel] = []
    warnings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class PipelineContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    evaluation_attempt_id: UUID
    execution_outputs: List[Dict[str, Any]]
    benchmark: Dict[str, Any]
    dataset: Optional[Dict[str, Any]] = None
    configuration: Dict[str, Any]
    artifacts: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

class EvaluationPipeline(Protocol):
    def evaluate(self, context: PipelineContext) -> EvaluationResultBundle:
        """Executes the evaluation pipeline against the provided context."""
        ...
