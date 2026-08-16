import re
import uuid
from ..core.cache import ReportCache
from ..exporters import ExportResult, get_exporter
from ..models.read_models import (
    CapabilityDashboardRead,
    HistoryEntryRead,
    LeaderboardRead,
    PaginatedReportRunsRead,
    ReportExportRead,
    ReportRunsFilter,
    ReportSummaryRead,
)
from ..services.queries import (
    CapabilityQueryService,
    HistoryQueryService,
    LeaderboardQueryService,
    RunQueryService,
)
from ..strategies.leaderboard import (
    CapabilityLeaderboardStrategy,
    OverallLeaderboardStrategy,
)


def _slugify(value: str) -> str:
    """Slugify a report title for a Content-Disposition filename."""
    slug = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-").lower()


class ReportingService:
    """
    The central business logic layer for reporting.
    Coordinates Query Services, Caching, and Strategies.
    """

    def __init__(
        self,
        cache: ReportCache,
        capability_query: CapabilityQueryService,
        leaderboard_query: LeaderboardQueryService,
        history_query: HistoryQueryService,
        run_query: RunQueryService | None = None,
    ):
        self.cache = cache
        self.capability_query = capability_query
        self.leaderboard_query = leaderboard_query
        self.history_query = history_query
        if run_query is None:
            # Fallback if not injected explicitly in old callers
            from ..repositories.reporting_repo import ReportingRepository

            self.run_query = RunQueryService(ReportingRepository(capability_query.repo.db))
        else:
            self.run_query = run_query

        self.leaderboard_strategies = {
            "overall": OverallLeaderboardStrategy(),
            "capability": CapabilityLeaderboardStrategy(),
        }

    def get_run_summary(self, run_id: uuid.UUID) -> ReportSummaryRead | None:
        cache_key = f"run_summary:{run_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached  # type: ignore

        data = self.run_query.get_run_summary(run_id)
        if data and data.evaluation_status in ("COMPLETED", "FAILED", "CANCELLED"):
            self.cache.set(cache_key, data)
        return data

    def get_runs_filtered(self, filter_obj: ReportRunsFilter) -> PaginatedReportRunsRead:
        return self.run_query.get_runs_filtered(filter_obj)

    def get_capability_dashboard(self, model_identifier: str) -> CapabilityDashboardRead | None:
        cache_key = f"capability_dashboard:{model_identifier}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached  # type: ignore

        data = self.capability_query.get_capability_dashboard(model_identifier)
        if data:
            self.cache.set(cache_key, data)
        return data

    def get_leaderboard(self, strategy_name: str, limit: int = 10) -> LeaderboardRead:
        cache_key = f"leaderboard:{strategy_name}:{limit}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached  # type: ignore

        strategy = self.leaderboard_strategies.get(strategy_name, OverallLeaderboardStrategy())
        data = strategy.execute(self.leaderboard_query, limit=limit)

        self.cache.set(cache_key, data)
        return data

    def get_history(self, limit: int = 50, offset: int = 0) -> tuple[list[HistoryEntryRead], int]:
        return self.history_query.get_paginated_history(limit, offset)

    def build_report_export(
        self,
        run_id: uuid.UUID,
        include_prompt: bool = False,
        include_expected_output: bool = False,
        execution_meta: dict | None = None,
    ) -> ReportExportRead | None:
        """Build the machine-readable export document for a persisted report.

        ``execution_meta`` may carry truthful agent-run context (steps, tool
        calls, provider chain, duration) for executions driven by an in-memory
        agent task. No data is fabricated: unmatched executions export only
        what genuinely exists in the database.
        """
        return self.run_query.get_report_export(
            run_id,
            include_prompt=include_prompt,
            include_expected_output=include_expected_output,
            execution_meta=execution_meta,
        )

    def export_run_results(
        self,
        run_id: uuid.UUID,
        format_type: str,
        include_prompt: bool = False,
        include_expected_output: bool = False,
        execution_meta: dict | None = None,
        document: ReportExportRead | None = None,
    ) -> ExportResult:
        exporter = get_exporter(format_type)
        if not exporter:
            raise ValueError(f"Export format '{format_type}' is not supported.")

        if document is None:
            document = self.build_report_export(
                run_id,
                include_prompt=include_prompt,
                include_expected_output=include_expected_output,
                execution_meta=execution_meta,
            )

        if format_type.lower() == "csv":
            # CSV is inherently row-based: export the per-case rows (possibly []).
            export_result = exporter.export(document.results if document else [])
        else:
            export_result = exporter.export(document if document is not None else [])

        if document and document.report:
            stem = _slugify(document.report.title) or "report"
            version = (document.report.version or "").lstrip("v")
            export_result.filename_stem = f"{stem}-v{version}" if version else stem

        return export_result
