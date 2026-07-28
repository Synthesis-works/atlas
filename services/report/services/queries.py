import uuid
from atlas_db.models.authoring import Capability
from atlas_db.models.execution import ExecutionStatus

from ..models.read_models import (
    CapabilityDashboardRead,
    CapabilityScoreRead,
    HistoryEntryRead,
    LeaderboardEntryRead,
    LeaderboardRead,
    PaginatedReportRunsRead,
    ReportRunEntryRead,
    ReportRunsFilter,
    ReportRunStatus,
    ReportSummaryRead,
)
from ..repositories.reporting_repo import ReportingRepository


def map_execution_to_report_status(
    run_status: ExecutionStatus, has_profile: bool
) -> ReportRunStatus:
    if run_status == ExecutionStatus.COMPLETED:
        return ReportRunStatus.COMPLETED
    elif run_status == ExecutionStatus.RUNNING:
        return ReportRunStatus.RUNNING
    elif run_status == ExecutionStatus.EVALUATING:
        return ReportRunStatus.EVALUATING
    elif run_status in (
        ExecutionStatus.FAILED,
        ExecutionStatus.TIMED_OUT,
        ExecutionStatus.RETRYING,
    ):
        return ReportRunStatus.FAILED
    elif run_status in (ExecutionStatus.CANCELLED, ExecutionStatus.CANCELLING):
        return ReportRunStatus.CANCELLED
    elif run_status in (
        ExecutionStatus.QUEUED,
        ExecutionStatus.SCHEDULED,
        ExecutionStatus.STARTING,
        ExecutionStatus.DRAFT,
    ):
        return ReportRunStatus.PENDING
    return ReportRunStatus.PENDING


class CapabilityQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def get_capability_dashboard(self, model_identifier: str) -> CapabilityDashboardRead | None:
        profile = self.repo.get_latest_capability_profile(model_identifier)
        if not profile:
            return None

        scores = []
        for score_model in profile.scores:
            cap_name = f"cap_{score_model.capability_id}"
            try:
                cap_obj = self.repo.db.get(Capability, score_model.capability_id)
                if cap_obj and cap_obj.name:
                    cap_name = cap_obj.name
            except Exception:
                pass
            scores.append(
                CapabilityScoreRead(
                    capability_name=cap_name,
                    score=score_model.score,
                )
            )

        return CapabilityDashboardRead(
            model_identifier=model_identifier,
            overall_score=profile.overall_score or 0.0,
            scores=scores,
        )


class RunQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def get_run_summary(self, run_id: uuid.UUID) -> ReportSummaryRead | None:
        detail = self.repo.get_run_detail(run_id)
        if not detail:
            return None

        run_obj, bv_obj, b_obj, profile_obj = detail
        eval_status = map_execution_to_report_status(run_obj.status, profile_obj is not None)

        scores = []
        if profile_obj and profile_obj.scores:
            for score_model in profile_obj.scores:
                cap_name = f"cap_{score_model.capability_id}"
                try:
                    cap_obj = self.repo.db.get(Capability, score_model.capability_id)
                    if cap_obj and cap_obj.name:
                        cap_name = cap_obj.name
                except Exception:
                    pass
                scores.append(
                    CapabilityScoreRead(
                        capability_name=cap_name,
                        score=score_model.score,
                    )
                )

        b_id = b_obj.id if b_obj else (bv_obj.benchmark_id if bv_obj else uuid.UUID(int=0))
        b_name = b_obj.name if b_obj else "Unknown Benchmark"
        b_version = bv_obj.version_string if bv_obj else "unknown"

        return ReportSummaryRead(
            run_id=run_obj.id,
            benchmark_id=b_id,
            benchmark_name=b_name,
            benchmark_version=b_version,
            target_model=run_obj.target_model,
            evaluation_status=eval_status,
            started_at=run_obj.started_at,
            completed_at=run_obj.completed_at,
            overall_score=profile_obj.overall_score if profile_obj else None,
            scores=scores,
        )

    def get_runs_filtered(self, filter_obj: ReportRunsFilter) -> PaginatedReportRunsRead:
        rows, total = self.repo.get_runs_filtered(filter_obj)
        items = []
        for run_obj, bv_obj, b_obj, profile_obj in rows:
            eval_status = map_execution_to_report_status(run_obj.status, profile_obj is not None)
            b_id = b_obj.id if b_obj else (bv_obj.benchmark_id if bv_obj else uuid.UUID(int=0))
            b_version = bv_obj.version_string if bv_obj else "unknown"

            items.append(
                ReportRunEntryRead(
                    run_id=run_obj.id,
                    benchmark_id=b_id,
                    benchmark_version=b_version,
                    target_model=run_obj.target_model,
                    evaluation_status=eval_status,
                    started_at=run_obj.started_at,
                    completed_at=run_obj.completed_at,
                    overall_score=profile_obj.overall_score if profile_obj else None,
                )
            )

        page_num = (filter_obj.offset // filter_obj.limit) + 1 if filter_obj.limit > 0 else 1
        return PaginatedReportRunsRead(
            items=items,
            total=total,
            page=page_num,
            size=filter_obj.limit,
        )

    def get_run_export_data(
        self,
        run_id: uuid.UUID,
        include_prompt: bool = False,
        include_expected_output: bool = False,
    ) -> list["RunExportRowRead"]:
        from ..models.read_models import RunExportRowRead

        rows = self.repo.get_run_export_data(run_id)
        results = []
        for run_obj, bv_obj, mo_obj, eval_obj, tc_obj in rows:
            eval_status = map_execution_to_report_status(run_obj.status, eval_obj is not None).value
            b_id = bv_obj.benchmark_id if bv_obj else uuid.UUID(int=0)
            b_version = bv_obj.version_string if bv_obj else "unknown"

            row = RunExportRowRead(
                run_id=run_obj.id,
                benchmark_id=b_id,
                benchmark_version=b_version,
                model_identifier=run_obj.target_model,
                execution_status=run_obj.status.value,
                evaluation_status=eval_status,
                started_at=run_obj.started_at,
                completed_at=run_obj.completed_at,
                test_case_id=mo_obj.test_case_id,
                category=None,
                difficulty=None,
                raw_output=mo_obj.raw_output,
                tokens_used=mo_obj.tokens_used,
                latency_ms=mo_obj.duration_ms,
                passed=eval_obj.passed if eval_obj else False,
                confidence=eval_obj.confidence if eval_obj else None,
                failure_reasons=eval_obj.failure_reasons if eval_obj else None,
            )

            if include_prompt and tc_obj:
                row.prompt = tc_obj.input_data

            if include_expected_output and tc_obj:
                row.expected_output = tc_obj.expected_output

            results.append(row)

        return results


class LeaderboardQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def get_overall_leaderboard(self, limit: int = 10) -> LeaderboardRead:
        data = self.repo.get_overall_leaderboard_data(limit=limit)
        entries = []
        for rank, (model, score) in enumerate(data, start=1):
            entries.append(
                LeaderboardEntryRead(rank=rank, model_identifier=model, score=score or 0.0)
            )
        return LeaderboardRead(strategy="overall", entries=entries)


class HistoryQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    def get_paginated_history(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[HistoryEntryRead], int]:
        runs, total = self.repo.get_history(limit, offset)

        items = []
        for run in runs:
            items.append(
                HistoryEntryRead(
                    run_id=run.id,
                    target_model=run.target_model,
                    status=run.status,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    passed=None,
                )
            )
        return items, total


class TrendQueryService:
    def __init__(self, repo: ReportingRepository):
        self.repo = repo

    pass
