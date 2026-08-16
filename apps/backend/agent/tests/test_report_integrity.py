"""Regression tests for report integrity:
#4 benchmark_id must be the real benchmark UUID (or null), never Report.id.
#5 created_at must originate from the persisted report version, never a hardcoded value.
#5G GenerateReportTool must persist ReportMetric rows only from real evaluation data.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.evaluation import (
    CapabilityProfile,
    EvaluationResult,
    EvaluationStrategy,
    EvaluationStrategyVersion,
    EvaluationStatus,
    StrategyType,
)
from atlas_db.models.execution import Execution, ExecutionStatus, ModelOutput
from atlas_db.models.reporting import Report, ReportMetric, ReportVersion
from atlas_db.models.tasks import Task, TestCase
from apps.backend.agent.state import AgentTask, AgentTaskStatus
from apps.backend.agent.tools.evaluation_tools import GenerateReportTool
from apps.backend.routers.agent import _agent_tasks_db


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


def _register_task(execution_id):
    task = AgentTask(
        goal="Integrity test",
        status=AgentTaskStatus.COMPLETED,
        execution_ids=[str(execution_id)],
    )
    _agent_tasks_db[task.task_id] = task
    return str(task.task_id)


def _seed_resolvable_chain(db):
    """Seeds Benchmark -> BenchmarkVersion -> Execution and returns their ids."""
    benchmark = Benchmark(
        id=uuid.uuid4(), project_id=uuid.uuid4(), name="Integrity Benchmark"
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


def _seed_evaluation(db, execution_id):
    """Seeds Task, TestCase, ModelOutputs, EvaluationResults and a CapabilityProfile."""
    task = Task(
        id=uuid.uuid4(),
        benchmark_version_id=execution_id,
        name="Integrity Task",
        order_index=0,
    )
    db.add(task)
    db.flush()

    test_case = TestCase(
        id=uuid.uuid4(),
        task_id=task.id,
        input_data={"q": "1+1"},
        expected_output={"a": "2"},
    )
    db.add(test_case)
    db.flush()

    strategy = EvaluationStrategy(
        id=uuid.uuid4(), name="exact_match", type=StrategyType.EXACT_MATCH
    )
    db.add(strategy)
    db.flush()
    strategy_version = EvaluationStrategyVersion(
        id=uuid.uuid4(), strategy_id=strategy.id, version_string="1.0.0"
    )
    db.add(strategy_version)
    db.flush()

    output_1 = ModelOutput(
        id=uuid.uuid4(), execution_id=execution_id, test_case_id=test_case.id, raw_output="2"
    )
    output_2 = ModelOutput(
        id=uuid.uuid4(), execution_id=execution_id, test_case_id=test_case.id, raw_output="3"
    )
    db.add_all([output_1, output_2])
    db.flush()

    result_1 = EvaluationResult(
        id=uuid.uuid4(),
        model_output_id=output_1.id,
        strategy_version_id=strategy_version.id,
        status=EvaluationStatus.COMPLETED,
        passed=True,
    )
    result_2 = EvaluationResult(
        id=uuid.uuid4(),
        model_output_id=output_2.id,
        strategy_version_id=strategy_version.id,
        status=EvaluationStatus.COMPLETED,
        passed=False,
    )
    db.add_all([result_1, result_2])
    db.flush()

    profile = CapabilityProfile(
        id=uuid.uuid4(),
        execution_id=execution_id,
        evaluation_id=result_1.id,
        strategy_version_id=strategy_version.id,
        profile_version=1,
        overall_score=0.5,
    )
    db.add(profile)
    db.commit()

    return output_1.id, result_1.id


def test_report_benchmark_id_resolves_through_execution_chain(db_session):
    """#4: get_agent_report returns the real benchmark UUID, not Report.id."""
    from apps.backend.routers.agent import get_agent_report

    benchmark_id, benchmark_version_id, execution_id = _seed_resolvable_chain(db_session)

    report = Report(id=uuid.uuid4(), project_id=uuid.uuid4(), name="Integrity Report")
    db_session.add(report)
    db_session.flush()

    report_version = ReportVersion(
        id=uuid.uuid4(),
        report_id=report.id,
        version_string="1.0.0",
        execution_id=execution_id,
    )
    db_session.add(report_version)
    db_session.commit()

    result = get_agent_report(str(report_version.id), db=db_session)

    assert result["report_id"] == str(report_version.id)
    assert result["benchmark_id"] == str(benchmark_id)
    assert result["benchmark_id"] != str(report.id)
    assert result["execution_id"] == str(execution_id)


def test_report_benchmark_id_null_when_unresolvable(db_session):
    """#4: benchmark_id is null when the execution/benchmark chain cannot be resolved."""
    from apps.backend.routers.agent import get_agent_report

    report = Report(id=uuid.uuid4(), project_id=uuid.uuid4(), name="Orphan Report")
    db_session.add(report)
    db_session.flush()

    # ReportVersion with NO execution_id -> chain is unresolvable.
    report_version = ReportVersion(
        id=uuid.uuid4(), report_id=report.id, version_string="1.0.0", execution_id=None
    )
    db_session.add(report_version)
    db_session.commit()

    result = get_agent_report(str(report_version.id), db=db_session)

    assert result["benchmark_id"] is None
    assert result["execution_id"] is None


def test_report_benchmark_id_null_when_execution_dangling(db_session):
    """#4: benchmark_id is null when the execution's benchmark_version_id is dangling."""
    from apps.backend.routers.agent import get_agent_report

    report = Report(id=uuid.uuid4(), project_id=uuid.uuid4(), name="Dangling Report")
    db_session.add(report)
    db_session.flush()

    # Execution referencing a benchmark_version_id that has no benchmark_versions row.
    dangling_execution = Execution(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        benchmark_version_id=uuid.uuid4(),
        target_model="gemini-3.5-flash-lite",
        status=ExecutionStatus.FAILED,
    )
    db_session.add(dangling_execution)
    db_session.flush()

    report_version = ReportVersion(
        id=uuid.uuid4(),
        report_id=report.id,
        version_string="1.0.0",
        execution_id=dangling_execution.id,
    )
    db_session.add(report_version)
    db_session.commit()

    result = get_agent_report(str(report_version.id), db=db_session)

    assert result["benchmark_id"] is None


def test_generate_report_created_at_comes_from_persisted_version(db_session):
    """#5: GenerateReportTool returns created_at matching the persisted report_version."""
    _, _, execution_id = _seed_resolvable_chain(db_session)

    task_id = _register_task(execution_id)
    tool = GenerateReportTool()
    result = tool.execute(
        db=db_session,
        benchmark_id=str(uuid.uuid4()),
        title="Timestamp Integrity Report",
        task_id=task_id,
    )

    persisted = (
        db_session.query(ReportVersion)
        .filter(ReportVersion.id == uuid.UUID(result["report_id"]))
        .first()
    )
    assert persisted is not None
    assert persisted.created_at is not None
    assert result["created_at"] == persisted.created_at.isoformat()
    # Regression guard: the returned timestamp must never be the old hardcoded value.
    assert result["created_at"] != "2026-08-13T09:40:00Z"
    assert "2026-08-13T09:40:00Z" not in result["created_at"]


def test_generate_report_persists_real_report_metrics(db_session):
    """#5G: ReportMetric rows are written only from real evaluation data."""
    _, _, execution_id = _seed_resolvable_chain(db_session)
    _seed_evaluation(db_session, execution_id)

    task_id = _register_task(execution_id)
    tool = GenerateReportTool()
    result = tool.execute(
        db=db_session,
        benchmark_id=str(uuid.uuid4()),
        title="Metric Integrity Report",
        task_id=task_id,
    )

    report_version_id = uuid.UUID(result["report_id"])
    metrics = (
        db_session.query(ReportMetric)
        .filter(ReportMetric.report_version_id == report_version_id)
        .all()
    )
    metric_map = {m.metric_name: m.metric_value for m in metrics}

    # 2 outputs: 1 passed, 1 failed. overall_score 0.5 -> accuracy 50.0.
    assert metric_map.get("accuracy") == 50.0
    assert metric_map.get("total_evaluated") == 2.0
    assert metric_map.get("passed") == 1.0
    assert metric_map.get("failed") == 1.0


def test_generate_report_persists_no_metrics_without_evaluation(db_session):
    """#5G: no ReportMetric rows are written when no evaluation data exists."""
    _, _, execution_id = _seed_resolvable_chain(db_session)

    task_id = _register_task(execution_id)
    tool = GenerateReportTool()
    result = tool.execute(
        db=db_session,
        benchmark_id=str(uuid.uuid4()),
        title="Empty Metric Report",
        task_id=task_id,
    )

    report_version_id = uuid.UUID(result["report_id"])
    metrics = (
        db_session.query(ReportMetric)
        .filter(ReportMetric.report_version_id == report_version_id)
        .all()
    )
    assert metrics == []
