import abc
from typing import Any

from packages.evaluation_engine.domain.evaluator import RawMeasurements


class CapabilityProfile:
    def __init__(self, scores: dict[str, float], overall_score: float, explanation: dict[str, Any]):
        """
        :param scores: Vector mapping capability name (e.g. "Python", "Reasoning") to normalized score 0-100.
        :param overall_score: The derived overall score.
        :param explanation: Detailed breakdown and weights.
        """
        self.scores = scores
        self.overall_score = overall_score
        self.explanation = explanation


class BaseScoringStrategy(abc.ABC):
    """
    Scoring Engine Interface.
    Takes raw facts and outputs normalized capabilities.
    """

    @abc.abstractmethod
    def score(self, measurements: RawMeasurements) -> CapabilityProfile:
        pass
