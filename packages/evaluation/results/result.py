from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .status import EvaluationStatus

class EvaluationResult(BaseModel):
    id: str = Field(..., description="Unique evaluation ID")
    benchmark_id: str = Field(..., description="Benchmark identifier")
    task_id: str = Field(..., description="Task identifier")
    provider: str = Field(..., description="LLM Provider")
    model: str = Field(..., description="LLM Model")
    judge: str = Field(..., description="Judge used")
    status: EvaluationStatus = Field(..., description="Final status")
    expected: str = Field(..., description="Expected output")
    actual: str = Field(..., description="Raw output from LLM")
    normalized_output: str = Field(..., description="Extracted & Normalized output")
    latency_ms: int = Field(..., description="Execution latency in ms")
    score: float = Field(default=0.0, description="Numerical score")
    confidence: float = Field(default=1.0, description="Confidence metric (0.0 to 1.0)")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
