import uuid
import time
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup local imports assuming this is run from the root directory or execution-service
import sys
import os

# To make this demo run from anywhere within the project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../packages/database')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from atlas_db.core.base import Base
from atlas_db.models.execution import (
    AtlasRun, AtlasTask, ExecutionWorker, RunEvent,
    RunStatus, TaskStatus, WorkerStatus, EventType
)
from services.execution_service.app.commands.run import CreateRunCommand, ValidateRunCommand
from services.execution_service.app.commands.worker import RegisterWorkerCommand, HeartbeatWorkerCommand
from services.execution_service.app.commands.task import ClaimTasksCommand, CompleteTaskCommand
from services.execution_service.app.controllers.run_controller import ExecutionController
from services.execution_service.app.controllers.worker_controller import WorkerController
from services.execution_service.app.controllers.task_controller import TaskController
from services.execution_service.app.events.publisher import PostgresEventPublisher

from services.execution_service.app.scheduler.core import AtlasScheduler
from services.execution_service.app.scheduler.policies import CompositePolicy, GlobalConcurrencyPolicy, PerWorkerConcurrencyPolicy

# --- Demo Setup Helpers ---

def setup_db():
    print("\n[System] Initializing in-memory SQLite database...")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def print_section(title: str):
    print(f"\n{'='*10} {title.upper()} {'='*10}")

def print_timeline(db_session, run_id):
    print("\nExecution Timeline:")
    print("-" * 40)
    events = db_session.query(RunEvent).filter_by(atlas_run_id=run_id).order_by(RunEvent.id).all()
    for e in events:
        time_str = e.created_at.strftime("%H:%M:%S") if e.created_at else "00:00:00"
        
        # Format the event line beautifully
        task_info = f" (Task {str(e.atlas_task_id)[:8]})" if e.atlas_task_id else ""
        print(f"{time_str} {e.type.value:<18} {task_info}")
    print("-" * 40)

def print_database_state(db_session, run_id, worker_id, task_ids):
    print("\nDatabase State:")
    print("-" * 40)
    
    # Run
    run = db_session.query(AtlasRun).filter_by(id=run_id).one()
    duration = (run.completed_at - run.started_at).total_seconds() if run.completed_at and run.started_at else 0
    print("AtlasRun")
    print(f"  Status:    {run.status.value}")
    print(f"  Progress:  {run.completed_tasks}/{run.total_tasks}")
    print(f"  Failed:    {run.failed_tasks}")
    print(f"  Duration:  {duration:.1f}s")
    
    # Worker
    worker = db_session.query(ExecutionWorker).filter_by(id=worker_id).one()
    print("\nWorker")
    print(f"  Status:    {worker.status.value}")
    print(f"  Platform:  {worker.platform}")
    print(f"  Load:      {worker.current_load}")
    
    # Tasks
    print("\nTasks")
    for tid in task_ids:
        task = db_session.query(AtlasTask).filter_by(id=tid).one()
        print(f"  {str(tid)[:8]} {task.status.value}")
        
    print("-" * 40)


# --- Demos ---

def demo_happy_path(db_session):
    print_section("Demo 1: Happy Path (End-to-End)")
    
    publisher = PostgresEventPublisher(db_session)
    run_ctrl = ExecutionController(db_session, publisher)
    worker_ctrl = WorkerController(db_session, publisher)
    task_ctrl = TaskController(db_session, publisher)
    
    # Mock pre-requisite UUIDs
    session_id = uuid.uuid4()
    bench_ver_id = uuid.uuid4()
    adapter_ver_id = uuid.uuid4()
    
    # 1. Register Worker
    worker_id = worker_ctrl.execute_register_worker(RegisterWorkerCommand(
        adapter_id=uuid.uuid4(),
        name="demo-worker",
        version="v1",
        hostname="demo-node-01",
        platform="linux"
    ))
    print(f"[*] Worker Registered. ID: {str(worker_id)[:8]}")
    
    # 2. Worker Heartbeat
    worker_ctrl.execute_heartbeat(HeartbeatWorkerCommand(
        worker_id=worker_id, current_load=0, health="healthy", active_tasks=0
    ))
    print("[*] Worker Heartbeat received (READY).")
    
    # 3. Create Run
    run_id = run_ctrl.execute_create_run(CreateRunCommand(
        session_id=session_id, benchmark_version_id=bench_ver_id,
        adapter_version_id=adapter_ver_id, target_model="mock-gpt"
    ))
    print(f"[*] Run Created. ID: {str(run_id)[:8]}")
    
    # 4. Mock Task Generation (Normally happens during Validation/Planning)
    print("[*] Mocking task generation (3 tasks)...")
    task_ids = []
    for _ in range(3):
        t = AtlasTask(
            atlas_run_id=run_id, test_case_id=uuid.uuid4(), 
            status=TaskStatus.PENDING
        )
        db_session.add(t)
        db_session.flush()
        task_ids.append(t.id)
    
    run = db_session.query(AtlasRun).filter_by(id=run_id).one()
    run.total_tasks = 3
    db_session.commit()
    
    # 5. Validate Run -> QUEUED
    run_ctrl.execute_validate_run(ValidateRunCommand(run_id=run_id))
    print("[*] Run Validated & Queued.")
    
    # 6. Initialize Scheduler
    policy = CompositePolicy([
        GlobalConcurrencyPolicy(max_running=100),
        PerWorkerConcurrencyPolicy(max_running=2) # Max 2 tasks per worker concurrently
    ])
    scheduler = AtlasScheduler(db_session, task_ctrl, publisher, policy)
    
    # 7. Run Scheduler Tick (Simulating background loop)
    print("\n[*] Scheduler Ticking...")
    scheduler.tick()
    print(scheduler.metrics.summary())
    
    # 8. Execute Tasks (Worker discovers claimed tasks and completes them)
    # The worker would normally pull its assigned tasks from an endpoint, but we mock it here.
    running_tasks = db_session.query(AtlasTask).filter_by(assigned_worker_id=worker_id, status=TaskStatus.RUNNING).all()
    print(f"\n[*] Worker found {len(running_tasks)} RUNNING tasks assigned to it.")
    
    for i, t in enumerate(running_tasks, 1):
        # Simulate execution
        time.sleep(0.5)
        
        # Complete
        task_ctrl.execute_complete_task(CompleteTaskCommand(
            worker_id=worker_id, task_id=t.id, raw_output=f"mock_answer_{i}"
        ))
        print(f"[*] Task {str(t.id)[:8]} Completed.")
        
        # Tick scheduler again because worker freed up capacity!
        scheduler.tick()

    # Show Results
    print("\n[*] Final Scheduler Metrics:", scheduler.metrics.summary())

    # Show Results
    print_timeline(db_session, run_id)
    print_database_state(db_session, run_id, worker_id, task_ids)

def demo_ownership_mismatch(db_session):
    print_section("Demo 2: Ownership Mismatch (Security)")
    
    publisher = PostgresEventPublisher(db_session)
    task_ctrl = TaskController(db_session, publisher)
    
    # Setup
    run_id = uuid.uuid4()
    db_session.add(AtlasRun(
        id=run_id, session_id=uuid.uuid4(), benchmark_version_id=uuid.uuid4(),
        adapter_version_id=uuid.uuid4(), target_model="mock", status=RunStatus.QUEUED, total_tasks=1
    ))
    
    task_id = uuid.uuid4()
    db_session.add(AtlasTask(
        id=task_id, atlas_run_id=run_id, test_case_id=uuid.uuid4(), status=TaskStatus.PENDING
    ))
    db_session.commit()
    
    worker_a = uuid.uuid4()
    worker_b = uuid.uuid4()
    
    print("[*] Worker A claims the task.")
    task_ctrl.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_a, max_tasks=1))
    
    print("[*] Worker B (Imposter) attempts to complete Worker A's task.")
    try:
        task_ctrl.execute_complete_task(CompleteTaskCommand(
            worker_id=worker_b, task_id=task_id, raw_output="hacked"
        ))
        print("[!] FATAL: Imposter successfully completed the task!")
    except PermissionError as e:
        print(f"[+] SUCCESS: Blocked imposter -> {str(e)}")

def demo_double_claim(db_session):
    print_section("Demo 3: Atomic Double Claiming")
    
    publisher = PostgresEventPublisher(db_session)
    task_ctrl = TaskController(db_session, publisher)
    
    # Setup
    run_id = uuid.uuid4()
    db_session.add(AtlasRun(
        id=run_id, session_id=uuid.uuid4(), benchmark_version_id=uuid.uuid4(),
        adapter_version_id=uuid.uuid4(), target_model="mock", status=RunStatus.QUEUED, total_tasks=1
    ))
    
    task_id = uuid.uuid4()
    db_session.add(AtlasTask(
        id=task_id, atlas_run_id=run_id, test_case_id=uuid.uuid4(), status=TaskStatus.PENDING
    ))
    db_session.commit()
    
    worker_a = uuid.uuid4()
    worker_b = uuid.uuid4()
    
    print("[*] Worker A claims the task.")
    claimed_a = task_ctrl.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_a, max_tasks=1))
    print(f"  -> Worker A received {len(claimed_a)} tasks.")
    
    print("[*] Worker B tries to claim the same task immediately after.")
    claimed_b = task_ctrl.execute_claim_tasks(ClaimTasksCommand(worker_id=worker_b, max_tasks=1))
    print(f"  -> Worker B received {len(claimed_b)} tasks.")
    
    if len(claimed_a) == 1 and len(claimed_b) == 0:
        print("[+] SUCCESS: Atomic locking prevented double-claiming.")
    else:
        print("[!] FATAL: Double claim prevention failed.")

if __name__ == "__main__":
    session = setup_db()
    
    demo_happy_path(session)
    demo_ownership_mismatch(session)
    demo_double_claim(session)
    
    print("\n[System] All Execution MVP Demos Completed.")
