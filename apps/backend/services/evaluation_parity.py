import uuid

from atlas_db.models.dataset import Dataset
from atlas_db.models.evaluation import (
    CapabilityProfile,
    CapabilityScore,
    EvaluationResult,
    EvaluationStatus,
)
from atlas_db.models.execution import Execution, ModelOutput
from atlas_db.models.reporting import Report, ReportMetric, ReportVersion
from atlas_db.models.tasks import Task, TestCase
from atlas_db.repositories.dataset import DatasetRepository, DatasetVersionRepository
from atlas_db.repositories.evaluation import (
    CapabilityProfileRepository,
    CapabilityScoreRepository,
    EvaluationResultRepository,
)
from atlas_db.repositories.execution import ExecutionRepository
from atlas_db.repositories.reporting import (
    ReportMetricRepository,
    ReportRepository,
    ReportVersionRepository,
)
from atlas_db.repositories.tasks import TaskRepository, TestCaseRepository
from sqlalchemy.orm import Session

from apps.backend.schemas.evaluation import (
    EvaluationResultsRead,
    ExecutionCompareItemRead,
    ExecutionCompareResponse,
    ExecutionEvaluationResultRead,
)
from apps.backend.schemas.evaluation_cases import (
    EvaluationCaseItem,
    EvaluationCaseWriteResponse,
    EvaluationCaseWritten,
)


class EvaluationParityService:
    """Legitimate REST service for agent evaluation capability parity.

    Provides read/write operations backed by the ORM repositories. Crucially,
    evaluation EXECUTION is not run here: runs are triggered through the async
    enqueue flow (POST .../evaluate -> Celery). This service only reads the
    resulting ``CapabilityProfile``/``EvaluationResult`` rows and supports
    authoring evaluation-case metadata and persisted reports.
    """

    def __init__(self, db: Session):
        self.db = db
        self.execution_repo = ExecutionRepository(db)
        self.eval_result_repo = EvaluationResultRepository(db)
        self.profile_repo = CapabilityProfileRepository(db)
        self.capability_score_repo = CapabilityScoreRepository(db)
        self.dataset_repo = DatasetRepository(db)
        self.dataset_version_repo = DatasetVersionRepository(db)
        self.task_repo = TaskRepository(db)
        self.test_case_repo = TestCaseRepository(db)
        self.report_repo = ReportRepository(db)
        self.report_version_repo = ReportVersionRepository(db)
        self.report_metric_repo = ReportMetricRepository(db)

    # ------------------------------------------------------------------ #
    # Evaluation results read
    # ------------------------------------------------------------------ #
    def get_evaluation_results(
        self, project_id: uuid.UUID, execution_id: uuid.UUID
    ) -> EvaluationResultsRead | None:
        execution = self.execution_repo.get(execution_id)
        if not execution or execution.project_id != project_id:
            return None

        profile = self._latest_profile(execution_id)
        results = (
            self.db.query(EvaluationResult)
            .join(ModelOutput, EvaluationResult.model_output_id == ModelOutput.id)
            .filter(ModelOutput.execution_id == execution_id)
            .order_by(EvaluationResult.created_at.asc())
            .all()
        )

        total_outputs = self.db.query(ModelOutput).filter_by(execution_id=execution_id).count()
        evaluated_outputs = len(results)
        passed_outputs = sum(1 for r in results if r.passed)
        status = EvaluationStatus.PARTIAL_SUCCESS.value if profile else "NOT_EVALUATED"
        if profile and evaluated_outputs and evaluated_outputs == passed_outputs:
            status = EvaluationStatus.COMPLETED.value

        result_reads = [
            ExecutionEvaluationResultRead(
                model_output_id=r.model_output_id,
                strategy_version_id=r.strategy_version_id,
                judge_id=r.judge_id,
                status=r.status.value if hasattr(r.status, "value") else str(r.status),
                passed=r.passed,
                confidence=r.confidence,
                reasoning=r.reasoning,
                raw_measurements=r.raw_measurements,
            )
            for r in results
        ]

        return EvaluationResultsRead(
            execution_id=execution_id,
            status=status,
            overall_score=profile.overall_score if profile else None,
            profile_id=profile.id if profile else None,
            total_outputs=total_outputs,
            evaluated_outputs=evaluated_outputs,
            passed_outputs=passed_outputs,
            results=result_reads,
        )

    def _latest_profile(self, execution_id: uuid.UUID) -> CapabilityProfile | None:
        profiles = (
            self.db.query(CapabilityProfile)
            .filter(CapabilityProfile.execution_id == execution_id)
            .order_by(CapabilityProfile.created_at.desc())
            .all()
        )
        return profiles[0] if profiles else None

    # ------------------------------------------------------------------ #
    # Evaluation case authoring
    # ------------------------------------------------------------------ #
    def create_evaluation_cases(
        self,
        project_id: uuid.UUID,
        dataset_id: uuid.UUID,
        items: list[EvaluationCaseItem],
    ) -> EvaluationCaseWriteResponse:
        dataset = self.dataset_repo.get(dataset_id)
        if not dataset or dataset.project_id != project_id:
            return None  # type: ignore[return-value]

        version_ids = {v.id for v in dataset.versions}
        written: list[EvaluationCaseWritten] = []
        skipped = 0

        for item in items:
            test_case = None
            if item.test_case_id:
                test_case = self.test_case_repo.get(item.test_case_id)
                if test_case:
                    task = self.task_repo.get(test_case.task_id)
                    if not task or task.dataset_version_id not in version_ids:
                        skipped += 1
                        continue
            elif item.task_id:
                task = self.task_repo.get(item.task_id)
                if not task or task.dataset_version_id not in version_ids:
                    skipped += 1
                    continue
                test_case = task.test_cases[0] if task.test_cases else None
                if test_case is None:
                    test_case = self.test_case_repo.create(
                        task_id=task.id, input_data={}, expected_output={}, commit=False
                    )
            else:
                skipped += 1
                continue

            if test_case is None:
                skipped += 1
                continue

            base_output = dict(test_case.expected_output) if test_case.expected_output else {}
            if item.expected_answer is not None:
                base_output["expected_answer"] = item.expected_answer
            if item.evaluation_method is not None:
                base_output["evaluation_method"] = item.evaluation_method
            if item.accepted_answers:
                base_output["accepted_answers"] = item.accepted_answers
            if item.rubric_criteria is not None:
                base_output["rubric_criteria"] = item.rubric_criteria

            self.test_case_repo.update(
                db_obj=test_case,
                obj_in={"expected_output": base_output},
                commit=False,
            )
            written.append(
                EvaluationCaseWritten(
                    test_case_id=test_case.id,
                    task_id=test_case.task_id,
                    evaluation_method=item.evaluation_method,
                    expected_answer=item.expected_answer,
                )
            )

        self.db.flush()
        return EvaluationCaseWriteResponse(dataset_id=dataset_id, written=written, skipped=skipped)

    # ------------------------------------------------------------------ #
    # Compare executions
    # ------------------------------------------------------------------ #
    def compare_executions(
        self, project_id: uuid.UUID, execution_ids: list[uuid.UUID]
    ) -> ExecutionCompareResponse:
        rows: list[ExecutionCompareItemRead] = []
        for execution_id in execution_ids:
            execution = self.execution_repo.get(execution_id)
            if not execution or execution.project_id != project_id:
                continue
            profile = self._latest_profile(execution_id)
            total_outputs = self.db.query(ModelOutput).filter_by(execution_id=execution_id).count()
            evaluated_outputs = (
                self.db.query(EvaluationResult)
                .join(ModelOutput, EvaluationResult.model_output_id == ModelOutput.id)
                .filter(ModelOutput.execution_id == execution_id)
                .count()
            )
            passed_outputs = (
                self.db.query(EvaluationResult)
                .join(ModelOutput, EvaluationResult.model_output_id == ModelOutput.id)
                .filter(
                    ModelOutput.execution_id == execution_id,
                    EvaluationResult.passed.is_(True),
                )
                .count()
            )
            rows.append(
                ExecutionCompareItemRead(
                    execution_id=execution_id,
                    target_model=execution.target_model,
                    overall_score=profile.overall_score if profile else None,
                    passed_outputs=passed_outputs,
                    total_outputs=total_outputs,
                    evaluated_outputs=evaluated_outputs,
                    rank=0,
                )
            )

        rows.sort(key=lambda r: (r.overall_score is None, -(r.overall_score or 0)))
        for idx, row in enumerate(rows, start=1):
            row.rank = idx
        return ExecutionCompareResponse(leaderboard=rows)

    # ------------------------------------------------------------------ #
    # Reports
    # ------------------------------------------------------------------ #
    def generate_report(
        self,
        project_id: uuid.UUID,
        created_by_id: uuid.UUID,
        title: str,
        benchmark_id: uuid.UUID | None,
        execution_id: uuid.UUID | None,
        version_string: str | None,
    ) -> Report | None:
        metrics: dict[str, float] = {}
        summary: str | None = None

        if execution_id:
            execution = self.execution_repo.get(execution_id)
            if not execution or execution.project_id != project_id:
                return None
            profile = self._latest_profile(execution_id)
            if profile:
                metrics["overall_score"] = profile.overall_score or 0.0
                metrics["evaluated_outputs"] = float(
                    self.db.query(EvaluationResult)
                    .join(ModelOutput, EvaluationResult.model_output_id == ModelOutput.id)
                    .filter(ModelOutput.execution_id == execution_id)
                    .count()
                )
                total = self.db.query(ModelOutput).filter_by(execution_id=execution_id).count()
                passed = (
                    self.db.query(EvaluationResult)
                    .join(ModelOutput, EvaluationResult.model_output_id == ModelOutput.id)
                    .filter(
                        ModelOutput.execution_id == execution_id,
                        EvaluationResult.passed.is_(True),
                    )
                    .count()
                )
                metrics["passed_outputs"] = float(passed)
                metrics["total_outputs"] = float(total)
                if profile.overall_score is not None:
                    summary = f"Overall score: {profile.overall_score:.4f}"

        report = (
            self.db.query(Report)
            .filter(Report.project_id == project_id, Report.name == title)
            .first()
        )
        if report is None:
            report = self.report_repo.create(project_id=project_id, name=title, commit=False)

        existing = self.db.query(ReportVersion).filter(ReportVersion.report_id == report.id).count()
        vs = version_string or f"v{existing + 1}"
        report_version = self.report_version_repo.create(
            report_id=report.id,
            version_string=vs,
            summary=summary,
            execution_id=execution_id,
            created_by_id=created_by_id,
            commit=False,
        )

        for metric_name, metric_value in metrics.items():
            self.report_metric_repo.create(
                report_version_id=report_version.id,
                metric_name=metric_name,
                metric_value=metric_value,
                commit=False,
            )

        self.db.flush()
        return report

    def list_reports(self, project_id: uuid.UUID) -> list[Report]:
        reports: list[Report] = self.db.query(Report).filter(Report.project_id == project_id).all()
        for report in reports:
            for version in report.versions:
                _ = version.metrics  # eager-load for serialization
        return reports
