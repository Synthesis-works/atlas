from atlas_db.models.evaluation import (
    CapabilityProfile,
    CapabilityScore,
    EvaluationResult,
    EvaluationResultDetail,
    EvaluationStrategy,
    EvaluationStrategyVersion,
    Judge,
)

from .base import BaseRepository


class EvaluationStrategyRepository(BaseRepository[EvaluationStrategy]):
    model = EvaluationStrategy


class EvaluationStrategyVersionRepository(BaseRepository[EvaluationStrategyVersion]):
    model = EvaluationStrategyVersion


class JudgeRepository(BaseRepository[Judge]):
    model = Judge


class EvaluationResultRepository(BaseRepository[EvaluationResult]):
    model = EvaluationResult


class CapabilityProfileRepository(BaseRepository[CapabilityProfile]):
    model = CapabilityProfile


class CapabilityScoreRepository(BaseRepository[CapabilityScore]):
    model = CapabilityScore


class EvaluationResultDetailRepository(BaseRepository[EvaluationResultDetail]):
    model = EvaluationResultDetail
