from typing import List, Dict, Any, Tuple
from uuid import UUID
from pydantic import BaseModel
from app.pipelines.base import MetricValueModel

class CapabilityScoreModel(BaseModel):
    capability_name: str
    score: float

class CapabilityProfileModel(BaseModel):
    adapter_version_id: UUID
    scores: List[CapabilityScoreModel]

class CapabilityEngine:
    """
    Derives high-level capability scores from raw metrics.
    No benchmark awareness. Simple weighted mapping logic.
    """
    def __init__(self, mapping_rules: Dict[str, str] = None):
        # Maps metric category to Capability name
        # Default simple mapping:
        self.mapping_rules = mapping_rules or {
            "CORRECTNESS": "Coding",
            "QUALITY": "Reasoning",
            "SAFETY": "Safety",
            "PERFORMANCE": "Efficiency"
        }

    def process(self, adapter_version_id: UUID, metrics: List[MetricValueModel]) -> CapabilityProfileModel:
        """Processes metrics to generate a capability profile."""
        
        # Group metrics by category
        category_scores: Dict[str, List[float]] = {}
        for metric in metrics:
            val = metric.normalized_value if metric.normalized_value is not None else metric.value
            category_scores.setdefault(metric.category, []).append(val)

        capability_scores = []
        for category, values in category_scores.items():
            cap_name = self.mapping_rules.get(category)
            if cap_name:
                avg_score = sum(values) / len(values) if values else 0.0
                capability_scores.append(CapabilityScoreModel(
                    capability_name=cap_name,
                    score=avg_score
                ))

        return CapabilityProfileModel(
            adapter_version_id=adapter_version_id,
            scores=capability_scores
        )
