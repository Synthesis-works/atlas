from uuid import UUID

from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.reporting import Report, ReportMetric, ReportVersion
from atlas_db.models.tasks import TestCase
from atlas_db.models.evaluation import CapabilityProfile, EvaluationResult
from atlas_db.models.execution import Execution as AtlasRun, ExecutionStatus, ModelOutput
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from services.report.models.read_models import ReportRunsFilter, ReportRunStatus


class ReportingRepository:
    """
    Abstracts direct database access for the Reporting Service.
    Queries the database and returns raw SQLAlchemy objects or basic tuples.
    Does NOT map to Read Models - that's the job of the Query Service / Reporting Service.
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
        stmt = (
            select(EvaluationResult)
            .join(ModelOutput, EvaluationResult.model_output_id == ModelOutput.id)
            .join(AtlasRun, ModelOutput.execution_id == AtlasRun.id)
            .where(AtlasRun.target_model == model_identifier)
        )
        return list(self.db.scalars(stmt))

    def get_capability_profiles_for_model(self, model_identifier: str) -> list[CapabilityProfile]:
        stmt = (
            select(CapabilityProfile)
            .join(AtlasRun, CapabilityProfile.execution_id == AtlasRun.id)
            .where(AtlasRun.target_model == model_identifier)
        )
        return list(self.db.scalars(stmt))

    def get_latest_capability_profile(self, model_identifier: str) -> CapabilityProfile | None:
        stmt = (
            select(CapabilityProfile)
            .join(AtlasRun, CapabilityProfile.execution_id == AtlasRun.id)
            .where(AtlasRun.target_model == model_identifier)
            .order_by(desc(AtlasRun.created_at))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def get_run_detail(
        self, run_id: UUID
    ) -> (
        tuple[AtlasRun, BenchmarkVersion | None, Benchmark | None, CapabilityProfile | None] | None
    ):
        stmt = (
            select(AtlasRun, BenchmarkVersion, Benchmark)
            .outerjoin(BenchmarkVersion, AtlasRun.benchmark_version_id == BenchmarkVersion.id)
            .outerjoin(Benchmark, BenchmarkVersion.benchmark_id == Benchmark.id)
            .where(AtlasRun.id == run_id)
        )
        row = self.db.execute(stmt).first()
        if not row:
            return None

        run_obj, bv_obj, b_obj = row[0], row[1], row[2]

        profile_stmt = (
            select(CapabilityProfile)
            .where(CapabilityProfile.execution_id == run_id)
            .order_by(desc(CapabilityProfile.profile_version))
            .limit(1)
        )
        profile_obj = self.db.scalars(profile_stmt).first()

        return run_obj, bv_obj, b_obj, profile_obj

    def get_runs_filtered(
        self, filter_obj: ReportRunsFilter
    ) -> tuple[
        list[tuple[AtlasRun, BenchmarkVersion | None, Benchmark | None, CapabilityProfile | None]],
        int,
    ]:
        stmt = (
            select(AtlasRun, BenchmarkVersion, Benchmark)
            .outerjoin(BenchmarkVersion, AtlasRun.benchmark_version_id == BenchmarkVersion.id)
            .outerjoin(Benchmark, BenchmarkVersion.benchmark_id == Benchmark.id)
        )
        count_stmt = (
            select(func.count(AtlasRun.id))
            .outerjoin(BenchmarkVersion, AtlasRun.benchmark_version_id == BenchmarkVersion.id)
            .outerjoin(Benchmark, BenchmarkVersion.benchmark_id == Benchmark.id)
        )

        if filter_obj.target_model:
            stmt = stmt.where(AtlasRun.target_model == filter_obj.target_model)
            count_stmt = count_stmt.where(AtlasRun.target_model == filter_obj.target_model)

        if filter_obj.benchmark_id and BenchmarkVersion:
            stmt = stmt.where(BenchmarkVersion.benchmark_id == filter_obj.benchmark_id)
            count_stmt = count_stmt.where(BenchmarkVersion.benchmark_id == filter_obj.benchmark_id)

        if filter_obj.benchmark_version and BenchmarkVersion:
            stmt = stmt.where(BenchmarkVersion.version_string == filter_obj.benchmark_version)
            count_stmt = count_stmt.where(
                BenchmarkVersion.version_string == filter_obj.benchmark_version
            )

        if filter_obj.status:
            # Map ReportRunStatus back to ExecutionStatus where applicable
            if filter_obj.status == ReportRunStatus.COMPLETED:
                stmt = stmt.where(AtlasRun.status == ExecutionStatus.COMPLETED)
                count_stmt = count_stmt.where(AtlasRun.status == ExecutionStatus.COMPLETED)
            elif filter_obj.status == ReportRunStatus.RUNNING:
                stmt = stmt.where(AtlasRun.status == ExecutionStatus.RUNNING)
                count_stmt = count_stmt.where(AtlasRun.status == ExecutionStatus.RUNNING)
            elif filter_obj.status == ReportRunStatus.EVALUATING:
                stmt = stmt.where(AtlasRun.status == ExecutionStatus.EVALUATING)
                count_stmt = count_stmt.where(AtlasRun.status == ExecutionStatus.EVALUATING)
            elif filter_obj.status == ReportRunStatus.FAILED:
                stmt = stmt.where(
                    AtlasRun.status.in_(
                        [
                            ExecutionStatus.FAILED,
                            ExecutionStatus.TIMED_OUT,
                            ExecutionStatus.RETRYING,
                        ]
                    )
                )
                count_stmt = count_stmt.where(
                    AtlasRun.status.in_(
                        [
                            ExecutionStatus.FAILED,
                            ExecutionStatus.TIMED_OUT,
                            ExecutionStatus.RETRYING,
                        ]
                    )
                )
            elif filter_obj.status == ReportRunStatus.CANCELLED:
                stmt = stmt.where(
                    AtlasRun.status.in_([ExecutionStatus.CANCELLED, ExecutionStatus.CANCELLING])
                )
                count_stmt = count_stmt.where(
                    AtlasRun.status.in_([ExecutionStatus.CANCELLED, ExecutionStatus.CANCELLING])
                )
            elif filter_obj.status == ReportRunStatus.PENDING:
                stmt = stmt.where(
                    AtlasRun.status.in_(
                        [
                            ExecutionStatus.QUEUED,
                            ExecutionStatus.SCHEDULED,
                            ExecutionStatus.STARTING,
                            ExecutionStatus.DRAFT,
                        ]
                    )
                )
                count_stmt = count_stmt.where(
                    AtlasRun.status.in_(
                        [
                            ExecutionStatus.QUEUED,
                            ExecutionStatus.SCHEDULED,
                            ExecutionStatus.STARTING,
                            ExecutionStatus.DRAFT,
                        ]
                    )
                )

        total = self.db.scalar(count_stmt) or 0

        stmt = (
            stmt.order_by(desc(AtlasRun.created_at))
            .limit(filter_obj.limit)
            .offset(filter_obj.offset)
        )
        rows = self.db.execute(stmt).all()

        results = []
        for row in rows:
            run_obj, bv_obj, b_obj = row[0], row[1], row[2]
            profile_stmt = (
                select(CapabilityProfile)
                .where(CapabilityProfile.execution_id == run_obj.id)
                .order_by(desc(CapabilityProfile.profile_version))
                .limit(1)
            )
            profile_obj = self.db.scalars(profile_stmt).first()
            results.append((run_obj, bv_obj, b_obj, profile_obj))

        return results, total

    def get_overall_leaderboard_data(self, limit: int = 10) -> list[tuple[str, float]]:
        stmt = (
            select(
                AtlasRun.target_model, func.avg(CapabilityProfile.overall_score).label("avg_score")
            )
            .join(CapabilityProfile, CapabilityProfile.execution_id == AtlasRun.id)
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

    def get_run_export_data(
        self, run_id: UUID
    ) -> list[
        tuple[AtlasRun, BenchmarkVersion | None, ModelOutput, EvaluationResult | None, TestCase]
    ]:
        stmt = (
            select(AtlasRun, BenchmarkVersion, ModelOutput, EvaluationResult, TestCase)
            .join(ModelOutput, ModelOutput.execution_id == AtlasRun.id)
            .join(TestCase, TestCase.id == ModelOutput.test_case_id)
            .outerjoin(EvaluationResult, EvaluationResult.model_output_id == ModelOutput.id)
            .outerjoin(BenchmarkVersion, AtlasRun.benchmark_version_id == BenchmarkVersion.id)
            .where(AtlasRun.id == run_id)
        )
        return list(self.db.execute(stmt))  # type: ignore

    def get_report_export(
        self, run_id: UUID
    ) -> tuple[
        AtlasRun,
        ReportVersion | None,
        Report | None,
        BenchmarkVersion | None,
        Benchmark | None,
        list[ReportMetric],
    ] | None:
        """Resolve the persisted report artifact for an execution run.

        Returns the Execution, its latest ReportVersion (if any), the Report it
        belongs to, the resolved BenchmarkVersion/Benchmark (if the execution's
        benchmark_version_id points at a real row), and the version's metrics.
        Returns None when the execution itself does not exist.
        """
        execution = self.db.get(AtlasRun, run_id)
        if not execution:
            return None

        report_version = (
            self.db.query(ReportVersion)
            .filter(ReportVersion.execution_id == run_id)
            .order_by(desc(ReportVersion.created_at))
            .first()
        )

        report = None
        if report_version:
            report = self.db.get(Report, report_version.report_id)

        benchmark_version = None
        benchmark = None
        if execution.benchmark_version_id:
            benchmark_version = self.db.get(BenchmarkVersion, execution.benchmark_version_id)
            if benchmark_version:
                benchmark = self.db.get(Benchmark, benchmark_version.benchmark_id)

        metrics = list(report_version.metrics) if report_version else []

        return execution, report_version, report, benchmark_version, benchmark, metrics
