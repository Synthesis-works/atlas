from sqlalchemy.orm import Session
from .base import BaseRepository
from atlas_db.models.evaluation import EvaluationStrategy, EvaluationStrategyVersion, Judge, EvaluationResult, EvaluationResultDetail, CapabilityProfile, CapabilityScore

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
