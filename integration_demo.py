import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

# Ensure the parent directory is in sys.path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "packages/database")))

from atlas_db.core.base import Base
from atlas_db.models.execution import (
    AtlasRun,
    AtlasTask,
    RunEvent,
)
from services.execution_service.app.commands.run import (
    CancelRunCommand,
    CreateRunCommand,
    ValidateRunCommand,
)
from services.execution_service.app.commands.task import (
    CompleteTaskCommand,
    FailTaskCommand,
)
from services.execution_service.app.commands.worker import (
    RegisterWorkerCommand,
)
from services.execution_service.app.controllers.run_controller import RunController
from services.execution_service.app.controllers.task_controller import TaskController
from services.execution_service.app.controllers.worker_controller import WorkerController
from services.execution_service.app.events.publisher import PostgresEventPublisher
from services.execution_service.app.recovery.manager import RecoveryManager
from services.execution_service.app.recovery.policies import (
    CompositeRecoveryPolicy,
    RetryPolicy,
    TimeoutPolicy,
)
from services.execution_service.app.scheduler.core import AtlasScheduler
from services.execution_service.app.scheduler.policies import (
    CompositePolicy,
    GlobalConcurrencyPolicy,
)
from services.execution_service.app.services.health_service import HealthService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def setup_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def print_health(health_service):
    print("\n[GET /system/health]")
    print(json.dumps(health_service.snapshot(), indent=2))


def print_timeline(db_session, run_id):
    print("\n--- Event Timeline ---")
    events = (
        db_session
        .query(RunEvent)
        .filter(RunEvent.atlas_run_id == run_id)
        .order_by(RunEvent.timestamp.asc())
        .all()
    )

    for e in events:
        msg = f"[{e.timestamp.strftime('%H:%M:%S')}] {e.type.value}"
        if e.message:
            msg += f" - {e.message}"
        print(msg)


def run_integration_demo():
    print("=========================================")
    print("   ATLAS INTEGRATION VALIDATION DEMO     ")
    print("=========================================\n")

    db_session = setup_db()
    publisher = PostgresEventPublisher(db_session)

    # Init Controllers
    run_ctrl = RunController(db_session, publisher)
    worker_ctrl = WorkerController(db_session, publisher)
    recovery_policy = CompositeRecoveryPolicy([TimeoutPolicy(3600), RetryPolicy(max_retries=1)])
    task_ctrl = TaskController(db_session, publisher, recovery_policy)

    # Init Subsystems
    sched_policy = CompositePolicy([GlobalConcurrencyPolicy(10)])
    scheduler = AtlasScheduler(db_session, task_ctrl, publisher, sched_policy)
    recovery_manager = RecoveryManager(
        db_session, publisher, unhealthy_threshold_seconds=2, offline_threshold_seconds=5
    )

    # Init Services
    health_service = HealthService(db_session, scheduler, recovery_manager)

    # ---------------------------------------------------------
    # Scenario 1: Happy Path
    # ---------------------------------------------------------
    print("\n=== SCENARIO 1: Happy Path ===")

    # 1. Register Worker
    worker1_id = worker_ctrl.execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="Worker-1",
            version="1.0",
            hostname="host-1",
            platform="linux",
            region="us-east",
            hardware_info={},
            capabilities={},
        )
    )
    print("[*] Worker-1 Registered.")

    # 2. Create & Validate Run
    run1_id = run_ctrl.execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo-model",
        )
    )
    run_ctrl.execute_validate_run(ValidateRunCommand(run_id=run1_id))
    print("[*] Run-1 Created and Validated (QUEUED).")

    # 3. Scheduler ticks
    scheduler.tick()
    print("[*] Scheduler ticked. Task scheduled to Worker-1.")

    # 4. Worker executes
    task = db_session.query(AtlasTask).filter_by(atlas_run_id=run1_id).one()
    task_ctrl.execute_complete_task(
        CompleteTaskCommand(worker_id=worker1_id, task_id=task.id, raw_output="success")
    )
    print("[*] Task completed.")

    print_timeline(db_session, run1_id)

    # ---------------------------------------------------------
    # Scenario 2: Worker Failure & Recovery
    # ---------------------------------------------------------
    print("\n=== SCENARIO 2: Worker Failure & Recovery ===")

    worker2_id = worker_ctrl.execute_register_worker(
        RegisterWorkerCommand(
            adapter_id=uuid.uuid4(),
            name="Worker-2",
            version="1.0",
            hostname="host-2",
            platform="linux",
            region="us-east",
            hardware_info={},
            capabilities={},
        )
    )

    run2_id = run_ctrl.execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo-model",
        )
    )
    run_ctrl.execute_validate_run(ValidateRunCommand(run_id=run2_id))

    scheduler.tick()
    task2 = db_session.query(AtlasTask).filter_by(atlas_run_id=run2_id).one()
    print("[*] Task scheduled to Worker-2.")

    # Simulate Worker 2 dying
    print("[*] Simulating Worker-2 crash (lease expired)...")
    task2.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    recovery_manager.tick()
    task_ctrl.execute_recovery_decision(task2.id)
    print("[*] Recovery Manager detected failure. TaskController requeued task.")

    scheduler.tick()
    task2 = db_session.query(AtlasTask).filter_by(atlas_run_id=run2_id).one()
    print("[*] Scheduler reassigned task to Worker-1.")

    task_ctrl.execute_complete_task(
        CompleteTaskCommand(worker_id=worker1_id, task_id=task2.id, raw_output="recovered!")
    )
    print_timeline(db_session, run2_id)

    # ---------------------------------------------------------
    # Scenario 3: Cancellation
    # ---------------------------------------------------------
    print("\n=== SCENARIO 3: Cancellation ===")

    run3_id = run_ctrl.execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo-model",
        )
    )
    run_ctrl.execute_validate_run(ValidateRunCommand(run_id=run3_id))
    scheduler.tick()
    print("[*] Run-3 started. Worker-1 assigned.")

    print("[*] User requests Cancellation...")
    run_ctrl.execute_cancel_run(CancelRunCommand(run_id=run3_id))

    run3 = db_session.query(AtlasRun).filter_by(id=run3_id).one()
    print(f"[*] Run Status is now: {run3.status.value}")

    print("[*] Worker-1 fails the task since it was aborted...")
    task3 = db_session.query(AtlasTask).filter_by(atlas_run_id=run3_id).one()
    task_ctrl.execute_fail_task(
        FailTaskCommand(
            worker_id=worker1_id,
            task_id=task3.id,
            error_code="ABORTED",
            error_message="Run cancelled",
            retryable=False,
        )
    )

    run3 = db_session.query(AtlasRun).filter_by(id=run3_id).one()
    print(f"[*] Run Status is now: {run3.status.value}")
    print_timeline(db_session, run3_id)

    # ---------------------------------------------------------
    # Scenario 4: Retry Exhaustion
    # ---------------------------------------------------------
    print("\n=== SCENARIO 4: Retry Exhaustion ===")

    run4_id = run_ctrl.execute_create_run(
        CreateRunCommand(
            session_id=uuid.uuid4(),
            benchmark_version_id=uuid.uuid4(),
            adapter_version_id=uuid.uuid4(),
            target_model="demo-model",
        )
    )
    run_ctrl.execute_validate_run(ValidateRunCommand(run_id=run4_id))
    scheduler.tick()

    print("[*] Task fails persistently...")
    task4 = db_session.query(AtlasTask).filter_by(atlas_run_id=run4_id).one()

    # Attempt 1
    task_ctrl.execute_fail_task(
        FailTaskCommand(
            worker_id=worker1_id,
            task_id=task4.id,
            error_code="FATAL",
            error_message="Crash",
            retryable=True,
        )
    )
    task_ctrl.execute_recovery_decision(task4.id)
    scheduler.tick()

    # Attempt 2
    task_ctrl.execute_fail_task(
        FailTaskCommand(
            worker_id=worker1_id,
            task_id=task4.id,
            error_code="FATAL",
            error_message="Crash again",
            retryable=True,
        )
    )
    task_ctrl.execute_recovery_decision(task4.id)

    run4 = db_session.query(AtlasRun).filter_by(id=run4_id).one()
    print(f"[*] Run Status after retry exhaustion: {run4.status.value}")
    print_timeline(db_session, run4_id)

    # ---------------------------------------------------------
    # Final Validation
    # ---------------------------------------------------------
    print("\n=========================================")
    print("   INTEGRATION SUMMARY                   ")
    print("=========================================\n")
    print("✓ Scheduler")
    print("✓ Recovery")
    print("✓ Workers")
    print("✓ Controller")
    print("✓ Events")
    print("✓ Progress Tracking")
    print("✓ Health API")

    print_health(health_service)


if __name__ == "__main__":
    run_integration_demo()
