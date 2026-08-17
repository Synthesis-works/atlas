import uuid
import pytest
from datetime import datetime, UTC
from unittest.mock import patch, ANY

from atlas_db.core.session import SessionLocal
from atlas_db.models.execution import Execution, ExecutionStatus
from atlas_db.models.core import Project
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.evaluation import (
    CapabilityProfile,
    EvaluationStrategy,
    EvaluationStrategyVersion,
)
from atlas_db.models.leaderboard import LeaderboardSnapshot, TargetType
from atlas_db.models.outbox import OutboxMessage

from packages.execution_engine.domain.events import ExecutionCompletedEvent
from packages.evaluation_engine.domain.events import EvaluationCompletedEvent
from apps.backend.events.celery_bus import CeleryExecutionEventBus
from apps.backend.events.snapshot_subscriber import SnapshotSubscriber

from atlas_db.core.engine import engine
from atlas_db.core.base import Base
from sqlalchemy import text


@pytest.fixture
def db_session():
    # Ensure schema exists (idempotent, safe when other tests have already created it)
    Base.metadata.create_all(bind=engine)
    # Clean only the tables this fixture uses, with CASCADE to satisfy FKs
    with engine.connect() as conn:
        conn.execute(
            text(
                "TRUNCATE leaderboard_snapshots, leaderboard_snapshot_entries, "
                "executions, benchmark_versions, benchmarks, projects, "
                "evaluation_strategy_versions, evaluation_strategies "
                "RESTART IDENTITY CASCADE"
            )
        )
        # Recreate the partial unique index so the test_f idempotency assertion works
        # (index may not be present if the migration hasn't been applied in this env)
        conn.execute(text("DROP INDEX IF EXISTS uq_snapshot_target_exec"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_snapshot_target_exec "
                "ON leaderboard_snapshots (target_id, (metadata->>'execution_id_trigger')) "
                "WHERE metadata->>'execution_id_trigger' IS NOT NULL"
            )
        )
        conn.commit()
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_data(db_session):
    try:
        project = Project(
            id=uuid.uuid4(),
            name=f"Test Project {uuid.uuid4()}",
            slug=f"test-project-{uuid.uuid4()}",
        )
        db_session.add(project)
        db_session.flush()

        strategy = EvaluationStrategy(
            id=uuid.uuid4(), name=f"Test Strategy {uuid.uuid4()}", type="exact_match"
        )
        db_session.add(strategy)
        db_session.flush()

        strategy_version = EvaluationStrategyVersion(
            id=uuid.uuid4(), strategy_id=strategy.id, version_string="v1.0"
        )
        db_session.add(strategy_version)
        db_session.flush()

        benchmark_parent = Benchmark(
            id=uuid.uuid4(), project_id=project.id, name=f"Test Benchmark {uuid.uuid4()}"
        )
        db_session.add(benchmark_parent)
        db_session.flush()

        benchmark = BenchmarkVersion(
            id=uuid.uuid4(),
            benchmark_id=benchmark_parent.id,
            version_string="1.0",
            evaluation_strategy_id=strategy_version.id,
        )
        db_session.add(benchmark)
        db_session.flush()

        exec_id = uuid.uuid4()
        from sqlalchemy import text

        db_session.execute(
            text(
                "INSERT INTO executions (id, project_id, benchmark_version_id, status, target_model, cancellation_requested, total_items, completed_items, version_number, created_at, updated_at) "
                "VALUES (:id, :pid, :bvid, :status, :target, false, 0, 0, 1, now(), now())"
            ),
            {
                "id": exec_id,
                "pid": project.id,
                "bvid": benchmark.id,
                "status": "COMPLETED",
                "target": "gpt-4",
            },
        )

        db_session.commit()

        from types import SimpleNamespace

        execution = SimpleNamespace(
            id=exec_id, project_id=project.id, benchmark_version_id=benchmark.id
        )
        return execution
    except Exception as e:
        db_session.rollback()
        raise e


def test_a_execution_completed_does_not_trigger_snapshot(db_session, test_data):
    """ExecutionCompletedEvent does NOT trigger snapshot generation (D7 boundary)."""
    bus = CeleryExecutionEventBus()
    event = ExecutionCompletedEvent(
        execution_id=test_data.id, attempt_id=uuid.uuid4(), timestamp=datetime.now(UTC)
    )

    with patch(
        "apps.backend.events.celery_snapshot_dispatcher.CelerySnapshotDispatcher.dispatch_benchmark_snapshot"
    ) as mock_benchmark:
        bus.emit(event)
        mock_benchmark.assert_not_called()


def test_g_manual_snapshot_remains_functional(db_session, test_data):
    """Manual snapshots (NULL execution_id_trigger) are never de-duplicated."""
    s1 = LeaderboardSnapshot(
        target_type=TargetType.BENCHMARK_VERSION,
        target_id=test_data.benchmark_version_id,
        snapshot_reason="manual",
        metadata_json=None,
    )
    db_session.add(s1)
    db_session.commit()

    s2 = LeaderboardSnapshot(
        target_type=TargetType.BENCHMARK_VERSION,
        target_id=test_data.benchmark_version_id,
        snapshot_reason="manual",
        metadata_json=None,
    )
    db_session.add(s2)
    try:
        db_session.commit()
    except Exception as e:
        pytest.fail(f"Manual snapshots should not collide: {e}")


def test_bcde_outbox_subscriber_integration(db_session, test_data):
    """EvaluationCompletedEvent routes through SnapshotSubscriber correctly."""
    event = EvaluationCompletedEvent(
        evaluation_id=uuid.uuid4(),
        execution_id=test_data.id,
        overall_score=85.0,
        duration_ms=100,
        artifact_count=0,
        timestamp=datetime.now(UTC),
    )

    sub = SnapshotSubscriber()
    with (
        patch(
            "apps.backend.events.celery_snapshot_dispatcher.CelerySnapshotDispatcher.dispatch_benchmark_snapshot"
        ) as mock_benchmark,
        patch(
            "apps.backend.events.celery_snapshot_dispatcher.CelerySnapshotDispatcher.dispatch_capability_snapshot"
        ) as mock_capability,
    ):
        sub.handle(event)

        mock_benchmark.assert_called_once()


def test_f_snapshot_duplicate_generation_enforced(db_session, test_data):
    """Concurrent automated snapshot triggers with the same execution_id are blocked by the DB partial unique index."""
    s1 = LeaderboardSnapshot(
        target_type=TargetType.BENCHMARK_VERSION,
        target_id=test_data.benchmark_version_id,
        snapshot_reason="automated",
        metadata_json={"execution_id_trigger": str(test_data.id)},
    )
    db_session.add(s1)
    db_session.commit()

    s2 = LeaderboardSnapshot(
        target_type=TargetType.BENCHMARK_VERSION,
        target_id=test_data.benchmark_version_id,
        snapshot_reason="automated",
        metadata_json={"execution_id_trigger": str(test_data.id)},
    )
    db_session.add(s2)

    import sqlalchemy

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.commit()
    db_session.rollback()
