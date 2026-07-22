import os
import sys
import time
import uuid

import pytest

# Ensure the parent directory is in sys.path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packages/database"))
)

from app.commands.worker import HeartbeatWorkerCommand, RegisterWorkerCommand
from app.controllers.worker_controller import WorkerController
from app.events.publisher import PostgresEventPublisher
from atlas_db.core.base import Base
from atlas_db.models.execution import ExecutionWorker, WorkerStatus
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


def test_slice3a_worker_lifecycle(db_session):
    adapter_id = uuid.uuid4()
    publisher = PostgresEventPublisher(db_session)
    controller = WorkerController(db_session, publisher)

    # 1. Register Worker
    cmd_register = RegisterWorkerCommand(
        adapter_id=adapter_id,
        name="test-worker-1",
        version="v1.0.0",
        hostname="worker-node-1",
        platform="linux",
        region="us-east-1",
        capabilities={"models": ["gpt-4"]},
    )

    worker_id = controller.execute_register_worker(cmd_register)
    assert worker_id is not None

    worker = db_session.query(ExecutionWorker).filter_by(id=worker_id).one()
    assert worker.status == WorkerStatus.READY
    assert worker.hostname == "worker-node-1"
    assert worker.health == "healthy"

    # 2. Heartbeat
    time.sleep(0.01)  # ensure timestamp differs
    old_heartbeat = worker.last_heartbeat_at

    cmd_heartbeat = HeartbeatWorkerCommand(
        worker_id=worker_id, current_load=5, health="healthy", cpu_usage=45.5, ram_usage=2048.0
    )

    controller.execute_heartbeat(cmd_heartbeat)

    worker_after = db_session.query(ExecutionWorker).filter_by(id=worker_id).one()
    assert worker_after.last_heartbeat_at > old_heartbeat
    assert worker_after.current_load == 5

    # 3. Mark Offline
    controller.mark_offline(worker_id)
    worker_offline = db_session.query(ExecutionWorker).filter_by(id=worker_id).one()
    assert worker_offline.status == WorkerStatus.OFFLINE

    # 4. Heartbeat Recovers Status
    controller.execute_heartbeat(cmd_heartbeat)
    worker_recovered = db_session.query(ExecutionWorker).filter_by(id=worker_id).one()
    assert worker_recovered.status == WorkerStatus.READY
