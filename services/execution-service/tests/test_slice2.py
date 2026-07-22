import os
import sys
import uuid

import pytest

# Ensure the parent directory is in sys.path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packages/database"))
)

from app.commands.run import CreateRunCommand, ValidateRunCommand
from app.controllers.run_controller import ExecutionController  # type: ignore
from app.events.publisher import PostgresEventPublisher
from atlas_db.core.base import Base

# Import all models to ensure they are registered with Base.metadata
from atlas_db.models.execution import (
    AtlasRun,
    EventType,
    RunEvent,
    RunStatus,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_create_and_validate_run(db_session):
    # Setup prerequisites (bypassing normal business logic just to satisfy FKs if they are checked)
    # We create some mock UUIDs
    session_id = uuid.uuid4()
    bench_ver_id = uuid.uuid4()
    adapter_ver_id = uuid.uuid4()

    # SQLite in memory generally does not enforce FKs unless explicitly enabled.
    # We will test the controller logic directly.

    publisher = PostgresEventPublisher(db_session)
    controller = ExecutionController(db_session, publisher)

    # 1. Create Run
    cmd_create = CreateRunCommand(
        session_id=session_id,
        benchmark_version_id=bench_ver_id,
        adapter_version_id=adapter_ver_id,
        target_model="gpt-4",
        config={"fail_fast": True},
    )

    run_id = controller.execute_create_run(cmd_create)
    assert run_id is not None

    run = db_session.query(AtlasRun).filter_by(id=run_id).one()
    assert run.status == RunStatus.CREATED
    assert run.config == {"fail_fast": True}

    # Check Events
    events = db_session.query(RunEvent).filter_by(atlas_run_id=run_id).order_by(RunEvent.id).all()
    assert len(events) == 1
    assert events[0].type == EventType.RUN_CREATED
    assert "successfully" in events[0].message

    # 2. Validate Run
    cmd_validate = ValidateRunCommand(run_id=run_id)
    controller.execute_validate_run(cmd_validate)

    run = db_session.query(AtlasRun).filter_by(id=run_id).one()
    # It transitions from VALIDATING to QUEUED
    assert run.status == RunStatus.QUEUED

    # Check Events
    events = db_session.query(RunEvent).filter_by(atlas_run_id=run_id).order_by(RunEvent.id).all()
    assert len(events) == 3  # CREATED -> VALIDATING -> QUEUED
    assert events[1].type == EventType.RUN_VALIDATED
    assert events[2].type == EventType.RUN_VALIDATED
    assert "QUEUED" in events[2].message
