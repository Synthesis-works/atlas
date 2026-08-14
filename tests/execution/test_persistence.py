import threading
import time
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from atlas_db.core.base import Base
from packages.execution_engine.domain.clock import TestClock
from packages.execution_engine.domain.models import (
    Artifact,
    ArtifactType,
    AttemptStatus,
    Execution,
    ExecutionState,
)
from packages.execution_engine.persistence.repository import SqlAlchemyExecutionRepository

# Load all models for Base.metadata
import atlas_db.models  # noqa: F401
import packages.execution_engine.persistence.models  # noqa: F401
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.core import Organization, Project, User

# Try connecting to Postgres if available, else SQLite
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_execution_db")
try:
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        has_postgres = True
except Exception:
    has_postgres = False
    engine = create_engine("sqlite:///:memory:")

SessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_database):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def create_parent_records(session: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Creates Organization, Project, User, Benchmark, and BenchmarkVersion rows required for FK constraints."""
    org = Organization(name="Test Org", slug=f"test-org-{uuid.uuid4().hex[:8]}")
    session.add(org)
    session.flush()

    project = Project(
        name="Test Project", slug=f"test-project-{uuid.uuid4().hex[:8]}", org_id=org.id
    )
    user = User(
        email=f"test-{uuid.uuid4().hex[:8]}@example.com", full_name="Test User", org_id=org.id
    )
    session.add_all([project, user])
    session.flush()

    benchmark = Benchmark(name="Test Benchmark", project_id=project.id, author_id=user.id)
    session.add(benchmark)
    session.flush()

    bv = BenchmarkVersion(benchmark_id=benchmark.id, version_string="1.0.0", created_by_id=user.id)
    session.add(bv)
    session.commit()

    return project.id, bv.id, user.id


def test_persistence_roundtrip(db_session: Session):
    clock = TestClock(datetime.now(UTC))
    repo = SqlAlchemyExecutionRepository(db_session)

    project_id, bv_id, user_id = create_parent_records(db_session)

    # 1. Create pure domain aggregate
    exec_id = uuid.uuid4()
    worker_id = uuid.uuid4()

    execution = Execution(
        id=exec_id,
        project_id=project_id,
        benchmark_version_id=bv_id,
        created_by=user_id,
        status=ExecutionState.QUEUED,
        created_at=clock.now(),
        updated_at=clock.now(),
        max_retries=5,
    )

    # Mutate to SCHEDULED to get attempt + lease
    attempt = execution.begin_attempt(worker_id, clock, 300)
    execution.status = ExecutionState.SCHEDULED
    attempt.add_artifact(Artifact(uuid.uuid4(), attempt.id, ArtifactType.LOGS, "s3://logs"))

    # 2. Persist
    repo.save(execution)
    db_session.commit()
    db_session.expire_all()

    # 3. Reload
    reloaded = repo.get(exec_id)

    # 4. Deep Equality Check
    assert reloaded is not None
    assert reloaded.id == exec_id
    assert reloaded.benchmark_version_id == bv_id
    assert reloaded.status == ExecutionState.SCHEDULED
    assert reloaded.max_retries == 5
    assert len(reloaded.attempts) == 1

    rl_attempt = reloaded.attempts[0]
    assert rl_attempt.id == attempt.id
    assert rl_attempt.attempt_number == 1
    assert rl_attempt.status == AttemptStatus.IN_PROGRESS

    assert rl_attempt.lease is not None
    assert rl_attempt.lease.worker_id == worker_id

    assert len(rl_attempt.artifacts) == 1
    assert rl_attempt.artifacts[0].type == ArtifactType.LOGS
    assert rl_attempt.artifacts[0].storage_uri == "s3://logs"


@pytest.mark.skipif(not has_postgres, reason="Concurrency SKIP LOCKED test requires PostgreSQL")
def test_concurrency_skip_locked(setup_database):
    """
    Test that two concurrent workers do not acquire the same queued execution.
    Worker 1 acquires the lock and sleeps.
    Worker 2 attempts to find schedulable executions and should get NOTHING due to skip_locked.
    """
    # Setup record
    session_setup = SessionLocal()
    repo_setup = SqlAlchemyExecutionRepository(session_setup)
    clock = TestClock(datetime.now(UTC))
    project_id, bv_id, user_id = create_parent_records(session_setup)
    exec_id = uuid.uuid4()
    execution = Execution(
        id=exec_id,
        project_id=project_id,
        benchmark_version_id=bv_id,
        created_by=user_id,
        status=ExecutionState.QUEUED,
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    repo_setup.save(execution)
    session_setup.commit()
    session_setup.close()

    results = []

    def worker_1():
        sess = SessionLocal()
        repo = SqlAlchemyExecutionRepository(sess)
        try:
            # Acquires lock and holds it
            ex = repo.find_schedulable(limit=1)
            if ex:
                results.append("W1_ACQUIRED")
            time.sleep(1)  # hold lock
        finally:
            sess.rollback()
            sess.close()

    def worker_2():
        time.sleep(0.2)  # ensure W1 runs first
        sess = SessionLocal()
        repo = SqlAlchemyExecutionRepository(sess)
        try:
            # Should skip locked row and return empty
            ex = repo.find_schedulable(limit=1)
            if not ex:
                results.append("W2_SKIPPED")
            else:
                results.append("W2_FAILED_TO_SKIP")
        finally:
            sess.rollback()
            sess.close()

    t1 = threading.Thread(target=worker_1)
    t2 = threading.Thread(target=worker_2)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert "W1_ACQUIRED" in results
    assert "W2_SKIPPED" in results
