"""Regression tests for the persisted report export (issue: JSON export was
returning `[]` for agent-created runs because it dumped per-case ModelOutput
rows instead of the actual ReportVersion/Report artifact).

Guardrails:
- The exported JSON document must contain the real persisted report metadata.
- Missing/invalid data must export as truthful nulls/empties, never fabricated.
- Agent-run context (steps, tool calls, provider chain, duration) is merged
  only from the real in-memory agent task store.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.execution import Execution, ExecutionStatus
from atlas_db.models.reporting import Report, ReportMetric, ReportVersion
from apps.backend.agent.state import AgentTask, AgentTaskStatus
from apps.backend.routers.agent import _agent_tasks_db
from apps.backend.routers.reporting import _collect_agent_execution_meta
from services.report.core.cache import NoopReportCache
from services.report.models.read_models import ReportExportRead
from services.report.repositories.reporting_repo import ReportingRepository
from services.report.services.queries import (
    CapabilityQueryService,
    HistoryQueryService,
    LeaderboardQueryService,
    RunQueryService,
)
from services.report.services.reporting import ReportingService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clear_agent_tasks():
    _agent_tasks_db.clear()
    yield
    _agent_tasks_db.clear()


def _build_service(db):
    repo = ReportingRepository(db)
    return ReportingService(
        cache=NoopReportCache(),
        capability_query=CapabilityQueryService(repo),
        leaderboard_query=LeaderboardQueryService(repo),
        history_query=HistoryQueryService(repo),
        run_query=RunQueryService(repo),
    )


def _seed_resolvable_chain(db):
    """Seeds Benchmark -> BenchmarkVersion -> Execution and returns their ids."""
    benchmark = Benchmark(
        id=uuid.uuid4(), project_id=uuid.uuid4(), name="Export Benchmark"
    )
    db.add(benchmark)
    db.flush()

    benchmark_version = BenchmarkVersion(
        id=uuid.uuid4(), benchmark_id=benchmark.id, version_string="1.0.0"
    )
    db.add(benchmark_version)
    db.flush()

    execution = Execution(
        id=uuid.uuid4(),
        project_id=benchmark.project_id,
        benchmark_version_id=benchmark_version.id,
        target_model="gemini-3.5-flash-lite",
        status=ExecutionStatus.COMPLETED,
    )
    db.add(execution)
    db.commit()

    return benchmark.id, benchmark_version.id, execution.id


def _seed_report_artifact(db, execution_id, title="Export Test Report", metrics=None):
    report = Report(id=uuid.uuid4(), project_id=uuid.uuid4(), name=title)
    db.add(report)
    db.flush()

    report_version = ReportVersion(
        id=uuid.uuid4(),
        report_id=report.id,
        version_string="1.0.0",
        summary="Generated summary.",
        execution_id=execution_id,
    )
    db.add(report_version)
    db.flush()

    for metric_name, metric_value in (metrics or {}).items():
        db.add(
            ReportMetric(
                id=uuid.uuid4(),
                report_version_id=report_version.id,
                metric_name=metric_name,
                metric_value=metric_value,
            )
        )
    db.commit()

    return report.id, report_version.id


def test_export_json_returns_real_report_artifact(db_session):
    """The JSON export must contain the persisted report, execution, benchmark
    and metrics — not a per-case dump (which was `[]` for agent runs)."""
    benchmark_id, benchmark_version_id, execution_id = _seed_resolvable_chain(db_session)
    report_id, report_version_id = _seed_report_artifact(
        db_session, execution_id, metrics={"accuracy": 50.0, "total_evaluated": 2.0}
    )

    result = _build_service(db_session).export_run_results(
        execution_id, format_type="json", execution_meta={}
    )

    assert result.mime_type == "application/json"
    assert result.filename_stem == "export-test-report-v1.0.0"

    document = ReportExportRead.model_validate_json(result.content)
    assert document.report is not None
    assert document.report.report_id == report_version_id
    assert document.report.title == "Export Test Report"
    assert document.report.version == "1.0.0"
    assert document.report.summary == "Generated summary."
    assert document.report.status == "published"

    assert document.execution is not None
    assert document.execution.id == execution_id
    assert document.execution.target_model == "gemini-3.5-flash-lite"
    assert document.execution.status == ExecutionStatus.COMPLETED.value

    assert document.benchmark is not None
    assert document.benchmark.id == benchmark_id
    assert document.benchmark.name == "Export Benchmark"
    assert document.benchmark.version == "1.0.0"

    metric_map = {m.metric_name: m.metric_value for m in document.metrics}
    assert metric_map == {"accuracy": 50.0, "total_evaluated": 2.0}


def test_export_json_truthful_nulls_for_dangling_benchmark(db_session):
    """#4 regression: an execution whose benchmark_version_id is dangling must
    export benchmark=null (truthful), never a fabricated benchmark, and
    empty metrics/results must not fail the export."""
    execution = Execution(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        target_model="gemini-3.5-flash-lite",
        status=ExecutionStatus.FAILED,
    )
    db_session.add(execution)
    db_session.flush()

    report = Report(id=uuid.uuid4(), project_id=uuid.uuid4(), name="Dangling Export Report")
    db_session.add(report)
    db_session.flush()

    report_version = ReportVersion(
        id=uuid.uuid4(),
        report_id=report.id,
        version_string="1.0.0",
        summary="No benchmark.",
        execution_id=execution.id,
    )
    db_session.add(report_version)
    db_session.commit()

    result = _build_service(db_session).export_run_results(
        execution.id, format_type="json", execution_meta={}
    )

    document = ReportExportRead.model_validate_json(result.content)
    assert document.report is not None
    assert document.report.title == "Dangling Export Report"
    assert document.benchmark is None
    assert document.metrics == []
    assert document.results == []
    assert document.execution is not None
    assert document.execution.status == ExecutionStatus.FAILED.value
    assert document.execution.duration_seconds is None


def test_export_json_merges_agent_execution_meta(db_session):
    """Agent-run context (provider chain, steps, tool calls, duration) is merged
    into the export only when the execution belongs to a real agent task."""
    _, _, execution_id = _seed_resolvable_chain(db_session)
    _seed_report_artifact(db_session, execution_id)

    started = datetime.now(UTC)
    task = AgentTask(
        goal="Export meta test",
        status=AgentTaskStatus.COMPLETED,
        execution_ids=[str(execution_id)],
        primary_provider="gemini",
        started_at=started,
        completed_at=started + timedelta(seconds=41),
        step_count=2,
        total_tool_calls=3,
    )
    task.record_trace(
        step=1,
        action="provider_decision_gemini",
        result={
            "provider": "gemini",
            "model": "gemini-3.5-flash-lite",
            "decision_type": "FINAL_RESPONSE",
            "latency_ms": 120,
        },
    )
    task.record_trace(
        step=1,
        action="provider_fallback",
        result={"failed_provider": "gemini", "next_provider": "groq", "reason": "rate limited"},
    )
    task.record_trace(
        step=2,
        action="provider_decision_groq",
        result={"provider": "groq", "model": "groq-model", "decision_type": "TOOL_CALL"},
    )
    _agent_tasks_db[task.task_id] = task

    service = _build_service(db_session)
    execution_meta = _collect_agent_execution_meta(execution_id)
    assert execution_meta["steps"] == 2
    assert execution_meta["tool_calls"] == 3
    assert execution_meta["provider_chain"] == ["gemini", "groq"]
    assert execution_meta["duration_seconds"] == 41.0

    result = service.export_run_results(
        execution_id, format_type="json", execution_meta=execution_meta
    )
    document = ReportExportRead.model_validate_json(result.content)

    assert document.execution is not None
    assert document.execution.steps == 2
    assert document.execution.tool_calls == 3
    assert document.execution.provider_chain == ["gemini", "groq"]
    assert document.execution.duration_seconds == 41.0


def test_export_json_unknown_execution_meta_is_empty(db_session):
    """Executions that do not belong to an agent task produce empty meta."""
    execution_id = uuid.uuid4()
    assert _collect_agent_execution_meta(execution_id) == {}
