"""Regression tests for BenchmarkVersion -> EvaluationStrategyVersion linkage.

Production incident (2026-08): agent-created BenchmarkVersions had
evaluation_strategy_id=NULL because CreateBenchmarkTool accepted an
evaluation_method argument but discarded it. The worker-side
EvaluationAppService then bailed with "No strategy attached to execution"
for every completed run, silently dropping evaluation.
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
    StrategyType,
)
from atlas_db.models.execution import Execution, ExecutionStatus, ModelOutput
from atlas_db.models.tasks import Task, TestCase
import packages.execution_engine.persistence.models  # noqa: F401 - registers ee_* tables
from apps.backend.agent.state import AgentTask, AgentTaskStatus
from apps.backend.agent.tools.benchmark_tools import CreateBenchmarkTool
from apps.backend.agent.tools.dataset_tools import CreateDatasetTool
from apps.backend.agent.tools.evaluation_tools import EvaluateRunTool, GenerateReportTool
from apps.backend.agent.tools.execution_tools import RunBenchmarkTool
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


# ---------------------------------------------------------------------------
# Resolver unit tests
# ---------------------------------------------------------------------------


def test_resolver_maps_methods_to_expected_strategy_types(db_session):
    from apps.backend.services.evaluation import resolve_strategy_version_for_method

    cases = {
        "exact_match": StrategyType.EXACT_MATCH,
        "numeric": StrategyType.EXACT_MATCH,
        "accepted_answers": StrategyType.EXACT_MATCH,
        "llm_judge": StrategyType.LLM_JUDGE,
        "rubric": StrategyType.LLM_JUDGE,
    }
    seen_versions = set()
    for method, expected_type in cases.items():
        sv = resolve_strategy_version_for_method(db_session, method)
        assert sv.id is not None
        assert sv.strategy.type == expected_type
        seen_versions.add(sv.id)
        db_session.expire_all()

    # All exact-match-family methods converge on ONE strategy version;
    # llm_judge family on another.
    assert len(seen_versions) == 2


def test_resolver_rejects_unknown_method(db_session):
    from apps.backend.services.evaluation import resolve_strategy_version_for_method

    with pytest.raises(ValueError, match="Unsupported evaluation_method"):
        resolve_strategy_version_for_method(db_session, "tarot_cards")


def test_resolver_defaults_to_exact_match_when_absent(db_session):
    from apps.backend.services.evaluation import resolve_strategy_version_for_method

    sv = resolve_strategy_version_for_method(db_session, None)
    assert sv.strategy.type == StrategyType.EXACT_MATCH


# ---------------------------------------------------------------------------
# CreateBenchmarkTool linkage
# ---------------------------------------------------------------------------


def test_create_benchmark_links_strategy_version(db_session):
    res = CreateBenchmarkTool().execute(
        db=db_session,
        name="Strategy Linked Benchmark",
        description="Tests that versions carry an evaluation strategy.",
        evaluation_method="exact_match",
    )
    bv = db_session.get(BenchmarkVersion, uuid.UUID(res["version_id"]))
    assert bv is not None
    assert bv.evaluation_strategy_id is not None

    sv = db_session.get(EvaluationStrategyVersion, bv.evaluation_strategy_id)
    assert sv is not None
    assert sv.strategy.type == StrategyType.EXACT_MATCH


def test_create_benchmark_llm_judge_maps_to_llm_judge_strategy(db_session):
    res = CreateBenchmarkTool().execute(
        db=db_session,
        name="Judge Benchmark",
        evaluation_method="llm_judge",
    )
    bv = db_session.get(BenchmarkVersion, uuid.UUID(res["version_id"]))
    sv = db_session.get(EvaluationStrategyVersion, bv.evaluation_strategy_id)
    assert sv.strategy.type == StrategyType.LLM_JUDGE


def test_create_benchmark_reuses_singleton_strategy_version(db_session):
    res_a = CreateBenchmarkTool().execute(db=db_session, name="Bench A")
    res_b = CreateBenchmarkTool().execute(
        db=db_session, name="Bench B", evaluation_method="numeric"
    )
    bv_a = db_session.get(BenchmarkVersion, uuid.UUID(res_a["version_id"]))
    bv_b = db_session.get(BenchmarkVersion, uuid.UUID(res_b["version_id"]))
    assert bv_a.evaluation_strategy_id == bv_b.evaluation_strategy_id


def test_create_benchmark_rejects_unknown_method_without_persisting(db_session):
    with pytest.raises(ValueError, match="Unsupported evaluation_method"):
        CreateBenchmarkTool().execute(
            db=db_session,
            name="Doomed Benchmark",
            evaluation_method="vibes",
        )
    assert db_session.query(Benchmark).count() == 0
    assert db_session.query(BenchmarkVersion).count() == 0


# ---------------------------------------------------------------------------
# RunBenchmarkTool guard against legacy/unlinked versions
# ---------------------------------------------------------------------------


def test_run_benchmark_rejects_version_without_strategy(db_session):
    bm = Benchmark(id=uuid.uuid4(), project_id=uuid.uuid4(), name="Legacy Benchmark")
    db_session.add(bm)
    db_session.flush()
    legacy_bv = BenchmarkVersion(
        id=uuid.uuid4(), benchmark_id=bm.id, version_string="1.0.0"
    )  # evaluation_strategy_id left NULL on purpose
    db_session.add(legacy_bv)
    db_session.commit()

    with pytest.raises(ValueError, match="no evaluation strategy"):
        RunBenchmarkTool().execute(
            db=db_session,
            benchmark_version_id=str(legacy_bv.id),
            dataset_version_id=str(uuid.uuid4()),
            target_models=["mock"],
        )


# ---------------------------------------------------------------------------
# Worker-side EvaluationAppService (the exact production failure)
# ---------------------------------------------------------------------------


class _CollectingPublisher:
    def __init__(self):
        self.events = []

    def publish(self, events):
        self.events.extend(events)


def _build_engine_registry():
    from packages.evaluation_engine.domain.evaluator import (
        BaseEvaluator,
        RawMeasurements,
    )
    from packages.evaluation_engine.domain.registry import EvaluationRegistry
    from packages.evaluation_engine.domain.scoring import (
        BaseScoringStrategy,
        CapabilityProfile as DomainProfile,
    )

    class StubEvaluator(BaseEvaluator):
        def prepare(self, context):
            pass

        def evaluate(self, execution_output):
            return RawMeasurements({"exact_match": True})

        def postprocess(self, measurements):
            pass

        def cleanup(self):
            pass

    class StubScoring(BaseScoringStrategy):
        def score(self, measurements):
            overall = 100.0 if measurements.raw_data.get("exact_match") else 0.0
            return DomainProfile(
                scores={"Reasoning": overall},
                overall_score=overall,
                explanation={"overall": overall},
            )

    registry = EvaluationRegistry()
    registry.register("exact_match", StubEvaluator, StubScoring)
    return registry


def _seed_completed_execution(db, strategy_version=None):
    bm = Benchmark(id=uuid.uuid4(), project_id=uuid.uuid4(), name=f"Bench {uuid.uuid4().hex[:6]}")
    db.add(bm)
    db.flush()
    bv = BenchmarkVersion(
        id=uuid.uuid4(),
        benchmark_id=bm.id,
        version_string="1.0.0",
        evaluation_strategy_id=strategy_version.id if strategy_version else None,
    )
    db.add(bv)
    db.flush()
    task = Task(id=uuid.uuid4(), benchmark_version_id=bv.id, name="t1", order_index=0)
    db.add(task)
    db.flush()
    tc = TestCase(
        id=uuid.uuid4(),
        task_id=task.id,
        input_data={"text": "Capital of France?"},
        expected_output={"expected_answer": "Paris"},
    )
    db.add(tc)
    db.flush()
    execution = Execution(
        id=uuid.uuid4(),
        project_id=bm.project_id,
        benchmark_version_id=bv.id,
        target_model="mock",
        status=ExecutionStatus.COMPLETED,
    )
    db.add(execution)
    db.flush()
    db.add(
        ModelOutput(
            id=uuid.uuid4(),
            execution_id=execution.id,
            test_case_id=tc.id,
            raw_output='{"completion": "Paris"}',
        )
    )
    db.commit()
    return bv, execution


def _build_engine_app_service(db, tmp_path):
    from packages.evaluation_engine.application.service import EvaluationAppService
    from packages.evaluation_engine.infrastructure.artifact_store import LocalArtifactStore

    return EvaluationAppService(
        session=db,
        registry=_build_engine_registry(),
        artifact_store=LocalArtifactStore(base_dir=str(tmp_path)),
        event_publisher=_CollectingPublisher(),
    )


def test_worker_evaluation_silently_skips_unlinked_strategy(db_session, tmp_path):
    """REPRODUCTION of the production failure: version without strategy ->
    'No strategy attached to execution' -> no evaluation artifacts at all."""
    _, execution = _seed_completed_execution(db_session, strategy_version=None)

    service = _build_engine_app_service(db_session, tmp_path)
    result = service.evaluate_execution(execution.id)

    assert result is None
    assert db_session.query(CapabilityProfile).count() == 0
    assert db_session.query(EvaluationResult).count() == 0


def test_worker_evaluation_succeeds_with_linked_strategy(db_session, tmp_path):
    strategy = EvaluationStrategy(name="Linked Exact Match", type=StrategyType.EXACT_MATCH)
    db_session.add(strategy)
    db_session.flush()
    sv = EvaluationStrategyVersion(strategy_id=strategy.id, version_string="v1.0")
    db_session.add(sv)
    db_session.commit()

    bv, execution = _seed_completed_execution(db_session, strategy_version=sv)

    service = _build_engine_app_service(db_session, tmp_path)
    service.evaluate_execution(execution.id)

    profiles = db_session.query(CapabilityProfile).all()
    assert len(profiles) == 1
    assert profiles[0].overall_score == 100.0
    assert profiles[0].strategy_version_id == sv.id
    assert db_session.query(EvaluationResult).count() == 1


# ---------------------------------------------------------------------------
# Full agent lifecycle: create -> dataset -> cases -> run -> evaluate -> report
# ---------------------------------------------------------------------------


def test_full_agent_lifecycle_with_strategy_linkage(db_session, tmp_path):
    # 1. Agent creates the benchmark (default method).
    bench_res = CreateBenchmarkTool().execute(
        db=db_session,
        name="Lifecycle Benchmark",
        description="End-to-end strategy linkage check.",
    )
    benchmark_id = bench_res["id"]
    version_id = bench_res["version_id"]
    bv = db_session.get(BenchmarkVersion, uuid.UUID(version_id))
    assert bv.evaluation_strategy_id is not None

    # 2. Dataset tasks are attached to the same benchmark version.
    ds_res = CreateDatasetTool().execute(
        db=db_session,
        benchmark_id=benchmark_id,
        name="lifecycle_ds",
        tasks=[
            {"id": "task_1", "input": "What is 2 + 2?", "expected_output": "4"},
        ],
    )
    dataset_version_id = ds_res["version_id"]

    # 3. Ground truth cases are persisted onto the test cases.
    from apps.backend.agent.tools.evaluation_tools import CreateEvaluationCaseTool

    case_res = CreateEvaluationCaseTool().execute(
        db=db_session,
        dataset_id=ds_res["id"],
        evaluation_cases=[
            {
                "task_id": "task_1",
                "expected_answer": "4",
                "evaluation_method": "exact_match",
                "accepted_answers": ["4", "four"],
            }
        ],
    )
    assert case_res["status"] == "CREATED"

    # 4. Runs dispatch cleanly because the version carries a strategy.
    run_res = RunBenchmarkTool().execute(
        db=db_session,
        benchmark_version_id=version_id,
        dataset_version_id=dataset_version_id,
        target_models=["mock", "mock"],
    )
    assert run_res["status"] == "DISPATCHED"
    exec_a, exec_b = (uuid.UUID(eid) for eid in run_res["execution_ids"])

    # 5. Simulate remote workers completing both executions.
    test_cases = db_session.query(TestCase).all()
    for exec_id in (exec_a, exec_b):
        execution = db_session.get(Execution, exec_id)
        execution.status = ExecutionStatus.COMPLETED
        for tc in test_cases:
            db_session.add(
                ModelOutput(
                    id=uuid.uuid4(),
                    execution_id=exec_id,
                    test_case_id=tc.id,
                    raw_output="4",
                    duration_ms=120,
                )
            )
    db_session.commit()

    # 6. Agent-driven evaluation produces a capability profile for run A.
    eval_res = EvaluateRunTool().execute(db=db_session, execution_id=str(exec_a))
    assert eval_res["status"] == "EVALUATED"
    assert eval_res["metrics"]["accuracy"] == 100.0

    # 7. Report generation records real metrics from the evaluation.
    agent_task = AgentTask(
        goal="lifecycle",
        status=AgentTaskStatus.COMPLETED,
        execution_ids=[str(exec_a)],
    )
    _agent_tasks_db[agent_task.task_id] = agent_task
    report_res = GenerateReportTool().execute(
        db=db_session, benchmark_id=benchmark_id, title="Lifecycle Report"
    )
    assert report_res["published"] is True

    # 8. Worker-driven engine evaluation succeeds for run B (previously the
    # exact codepath that logged "No strategy attached to execution").
    from packages.evaluation_engine.application.service import EvaluationAppService
    from packages.evaluation_engine.infrastructure.artifact_store import LocalArtifactStore

    engine = EvaluationAppService(
        session=db_session,
        registry=_build_engine_registry(),
        artifact_store=LocalArtifactStore(base_dir=str(tmp_path)),
        event_publisher=_CollectingPublisher(),
    )
    engine.evaluate_execution(exec_b)

    profiles = (
        db_session.query(CapabilityProfile).filter(CapabilityProfile.execution_id == exec_b).all()
    )
    assert len(profiles) == 1
    assert profiles[0].overall_score == 100.0
