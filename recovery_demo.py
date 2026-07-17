import sys
import os
import uuid
import time
from datetime import datetime, timezone, timedelta

# Ensure the parent directory is in sys.path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'packages/database')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from atlas_db.core.base import Base

from atlas_db.models.execution import (
    AtlasRun, AtlasTask, ExecutionWorker, TaskStatus, RunStatus, WorkerStatus, RunEvent
)

from services.execution_service.app.commands.run import CreateRunCommand, ValidateRunCommand
from services.execution_service.app.commands.worker import RegisterWorkerCommand, HeartbeatWorkerCommand
from services.execution_service.app.commands.task import ClaimTasksCommand, CompleteTaskCommand, FailTaskCommand
from services.execution_service.app.controllers.run_controller import RunController
from services.execution_service.app.controllers.worker_controller import WorkerController
from services.execution_service.app.controllers.task_controller import TaskController
from services.execution_service.app.events.publisher import PostgresEventPublisher

from services.execution_service.app.recovery.manager import RecoveryManager
from services.execution_service.app.recovery.policies import CompositeRecoveryPolicy, RetryPolicy, TimeoutPolicy, RecoveryAction

def setup_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def print_timeline(db_session, run_id):
    print("\n--- Event Timeline ---")
    events = db_session.query(RunEvent).filter(
        RunEvent.atlas_run_id == run_id
    ).order_by(RunEvent.timestamp.asc()).all()
    
    for e in events:
        msg = f"[{e.timestamp.strftime('%H:%M:%S')}] {e.type.value}"
        if e.message:
            msg += f" - {e.message}"
        print(msg)
    
    # Print global events (worker events)
    print("\n--- Global Worker Events ---")
    global_events = db_session.query(RunEvent).filter(
        RunEvent.atlas_run_id == None
    ).order_by(RunEvent.timestamp.asc()).all()
    
    for e in global_events:
        msg = f"[{e.timestamp.strftime('%H:%M:%S')}] {e.type.value}"
        if e.message:
            msg += f" - {e.message}"
        print(msg)

def run_demo():
    print("=========================================")
    print("   ATLAS RECOVERY MANAGER MVP DEMO       ")
    print("=========================================\n")

    db_session = setup_db()
    publisher = PostgresEventPublisher(db_session)
    
    # Controllers
    run_ctrl = RunController(db_session, publisher)
    worker_ctrl = WorkerController(db_session, publisher)
    
    policy = CompositeRecoveryPolicy([TimeoutPolicy(3600), RetryPolicy(max_retries=1)])
    task_ctrl = TaskController(db_session, publisher, policy)
    
    # Recovery Manager (thresholds set very low for demo)
    recovery_manager = RecoveryManager(
        db_session, publisher, 
        unhealthy_threshold_seconds=2, 
        offline_threshold_seconds=5
    )

    # --- Scenario 1: Worker dies -> Task requeued -> Worker B finishes ---
    print("\n--- SCENARIO 1: Worker Dies & Task Requeued ---")
    run_id = run_ctrl.execute_create_run(CreateRunCommand(
        session_id=uuid.uuid4(), benchmark_version_id=uuid.uuid4(), adapter_version_id=uuid.uuid4(), target_model="demo-model"
    ))
    task_id = db_session.query(AtlasTask).filter_by(atlas_run_id=run_id).first().id
    run_ctrl.execute_validate_run(ValidateRunCommand(run_id=run_id))
    
    worker_a_id = worker_ctrl.execute_register_worker(RegisterWorkerCommand(
        adapter_id=uuid.uuid4(), name="Worker-A", version="1.0", hostname="host-a", platform="linux", region="us-east", hardware_info={}, capabilities={}
    ))
    
    claimed = task_ctrl.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_a_id, max_tasks=1))
    print(f"[*] Worker-A claimed task. Simulating Worker-A dying...")
    
    # Simulate Worker A dying by forcing its lease to expire and heartbeat to be old
    task = db_session.query(AtlasTask).filter_by(id=claimed[0]).one()
    task.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    worker_a = db_session.query(ExecutionWorker).filter_by(id=worker_a_id).one()
    worker_a.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()
    
    # Recovery Manager Detects
    recovery_manager.tick()
    print(f"[*] Recovery Manager ticked. Leases expired: {recovery_manager.metrics.leases_expired}")
    
    # Simulated ExecutionController picking up the LEASE_EXPIRED event and deciding:
    action = task_ctrl.execute_recovery_decision(claimed[0])
    print(f"[*] Execution Controller evaluated policy: {action}")
    
    # Worker B comes online and claims the requeued task
    worker_b_id = worker_ctrl.execute_register_worker(RegisterWorkerCommand(
        adapter_id=uuid.uuid4(), name="Worker-B", version="1.0", hostname="host-b", platform="linux", region="us-east", hardware_info={}, capabilities={}
    ))
    claimed_b = task_ctrl.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_b_id, max_tasks=1))
    print(f"[*] Worker-B claimed task {claimed_b[0]} (attempt 2). Completing it...")
    
    task_ctrl.execute_complete_task(CompleteTaskCommand(worker_id=worker_b_id, task_id=claimed_b[0], raw_output="recovered!"))
    print_timeline(db_session, run_id)

    # --- Scenario 2: Worker misses heartbeat -> UNHEALTHY -> READY ---
    print("\n--- SCENARIO 2: Brief Network Hiccup (UNHEALTHY -> READY) ---")
    worker_c_id = worker_ctrl.execute_register_worker(RegisterWorkerCommand(
        adapter_id=uuid.uuid4(), name="Worker-C", version="1.0", hostname="host-c", platform="linux", region="us-east", hardware_info={}, capabilities={}
    ))
    
    worker_c = db_session.query(ExecutionWorker).filter_by(id=worker_c_id).one()
    worker_c.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=3) # > 2s unhealthy threshold, < 5s offline threshold
    db_session.commit()
    
    # Recovery manager detects unhealthy
    recovery_manager.tick()
    worker_c = db_session.query(ExecutionWorker).filter_by(id=worker_c_id).one()
    # Manual controller transition because event system isn't wired fully async
    worker_ctrl.execute_mark_unhealthy(worker_c_id) 
    worker_c = db_session.query(ExecutionWorker).filter_by(id=worker_c_id).one()
    print(f"[*] Worker-C missed heartbeat. Status: {worker_c.status.value}")
    
    # Heartbeat returns
    worker_ctrl.execute_heartbeat(HeartbeatWorkerCommand(worker_id=worker_c_id, current_load=0, health="healthy"))
    worker_c = db_session.query(ExecutionWorker).filter_by(id=worker_c_id).one()
    print(f"[*] Worker-C sent heartbeat. Status recovered to: {worker_c.status.value}")

    # --- Scenario 3: Task exceeds retry limit -> FAILED ---
    print("\n--- SCENARIO 3: Retry Limit Exceeded -> Run Failed ---")
    run2_id = run_ctrl.execute_create_run(CreateRunCommand(
        session_id=uuid.uuid4(), benchmark_version_id=uuid.uuid4(), adapter_version_id=uuid.uuid4(), target_model="demo-model"
    ))
    run_ctrl.execute_validate_run(ValidateRunCommand(run_id=run2_id))
    
    claimed2 = task_ctrl.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_c_id, max_tasks=1))
    task2_id = claimed2[0]
    
    print(f"[*] Worker-C claimed task {task2_id}. Failing it...")
    # Fails attempt 1 (Controller automatically retries inside execute_fail_task in real life, but for demo we will fail it via command, and let it stay FAILED. Wait, FailTaskCommand sets status=FAILED)
    # Actually, in our architecture, FailTaskCommand shouldn't instantly fail the task if retries are available. 
    # But for demo, let's just forcefully increment attempt to max, and then run recovery.
    task2 = db_session.query(AtlasTask).filter_by(id=task2_id).one()
    task2.attempt_number = 2 # Max retries is 1
    task2.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    
    # Recovery Manager Detects
    recovery_manager.tick()
    
    # Controller decides
    action = task_ctrl.execute_recovery_decision(task2_id)
    print(f"[*] Execution Controller evaluated policy for attempt 2: {action}")
    
    task2 = db_session.query(AtlasTask).filter_by(id=task2_id).one()
    print(f"[*] Task Status: {task2.status.value}")
    run2 = db_session.query(AtlasRun).filter_by(id=run2_id).one()
    print(f"[*] Run Status: {run2.status.value}")
    
    print_timeline(db_session, run2_id)


if __name__ == "__main__":
    run_demo()
