from atlas_db.models.evaluation import CapabilityProfile, EvaluationResult
from atlas_db.models.execution import Execution as AtlasRun, ModelOutput
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session


class ReportingRepository:
    """
    Abstracts direct database access for the Reporting Service.
    Queries the database and returns raw SQLAlchemy objects or basic tuples.
    Does NOT map to Read Models - that's the job of the Query Service.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_runs_for_model(
        self, model_identifier: str, limit: int = 100, offset: int = 0
    ) -> list[AtlasRun]:
        stmt = (
            select(AtlasRun)
            .where(AtlasRun.target_model == model_identifier)
            .order_by(desc(AtlasRun.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt))

    def get_evaluations_for_model(self, model_identifier: str) -> list[EvaluationResult]:
        # Get evaluation results joined with ModelOutput and AtlasRun
        stmt = (
            select(EvaluationResult)
            .join(ModelOutput, EvaluationResult.model_output_id == ModelOutput.id)
            .join(AtlasRun, ModelOutput.atlas_run_id == AtlasRun.id)
            .where(AtlasRun.target_model == model_identifier)
        )
        return list(self.db.scalars(stmt))

    def get_capability_profiles_for_model(self, model_identifier: str) -> list[CapabilityProfile]:
        stmt = (
            select(CapabilityProfile)
            .join(AtlasRun, CapabilityProfile.atlas_run_id == AtlasRun.id)
            .where(AtlasRun.target_model == model_identifier)
        )
        return list(self.db.scalars(stmt))

    def get_latest_capability_profile(self, model_identifier: str) -> CapabilityProfile | None:
        stmt = (
            select(CapabilityProfile)
            .join(AtlasRun, CapabilityProfile.atlas_run_id == AtlasRun.id)
            .where(AtlasRun.target_model == model_identifier)
            .order_by(desc(AtlasRun.created_at))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def get_overall_leaderboard_data(self, limit: int = 10) -> list[tuple[str, float]]:
        # A simple aggregation: average overall_score by target_model
        stmt = (
            select(
                AtlasRun.target_model, func.avg(CapabilityProfile.overall_score).label("avg_score")
            )
            .join(CapabilityProfile, CapabilityProfile.atlas_run_id == AtlasRun.id)
            .group_by(AtlasRun.target_model)
            .order_by(desc("avg_score"))
            .limit(limit)
        )
        return list(self.db.execute(stmt))  # type: ignore

    def get_history(self, limit: int = 50, offset: int = 0) -> tuple[list[AtlasRun], int]:
        stmt = select(AtlasRun).order_by(desc(AtlasRun.created_at)).limit(limit).offset(offset)
        items = list(self.db.scalars(stmt))

        count_stmt = select(func.count()).select_from(AtlasRun)
        total = self.db.scalar(count_stmt) or 0

        return items, total
