import json
import os
import sys
import time
from uuid import UUID, uuid4

import dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

dotenv.load_dotenv()

# Add project root and packages/database to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "database"))
)

from atlas_db.core.base import Base
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.execution import Execution
from atlas_db.models.core import Project, Organization

from apps.backend.agent.agent import AtlasAgent
from apps.backend.agent.memory import AgentMemoryManager, SemanticMemoryStore
from apps.backend.agent.providers.gemini import GeminiAgentProvider
from apps.backend.agent.state import AgentPermission, AgentTask, AgentTaskStatus
from apps.backend.agent.tools.registry import ToolRegistry


def main():
    print("=" * 80)
    print("      ATLAS REAL AGENT LEVEL-3 SMOKE TEST REPORT")
    print("=" * 80)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY environment variable is missing in .env!")
        sys.exit(1)

    print(f"[1] Verified GEMINI_API_KEY: Present ({api_key[:6]}...{api_key[-4:]})")

    # 1. Setup isolated disposable database
    db_file = f"./disposable_agent_test_{uuid4().hex[:6]}.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    print("[2] Initialized isolated disposable database schema.")

    # Create dummy organization & project for foreign keys
    org_id = uuid4()
    proj_id = UUID("00000000-0000-0000-0000-000000000001")
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    proj = Project(id=proj_id, org_id=org_id, name="Disposable Test Project", slug="test-proj")
    db.add(org)
    db.add(proj)
    db.commit()

    # 2. Check Ollama / Nomic semantic memory store
    print("\n--- Semantic Memory Store Verification ---")
    mem_store = SemanticMemoryStore()
    if mem_store.is_available:
        print(f"Ollama Online: True | Embedding Model: '{mem_store.provider.model}'")
        mem_store.add_memory(
            memory_id="mem-1",
            memory_type="historical_lesson",
            text="Python vulnerability detection datasets should cover exec(), eval(), and SQL injection flaws.",
            metadata={"source": "historical_benchmarks"},
        )
    else:
        print("Ollama Offline: True | Graceful Fallback Active (Core Agent execution unhindered)")

    from apps.backend.agent.providers.router import ProviderRouter

    # 3. Test Permission Checkpoint Flow & Provider Router
    print("\n--- Testing Permission Checkpoint Flow & Provider Router ---")
    provider_router = ProviderRouter(primary=GeminiAgentProvider(model="gemini-3.5-flash-lite"))
    registry = ToolRegistry()
    agent = AtlasAgent(provider=provider_router, registry=registry)

    restricted_task = AgentTask(
        goal="Create a benchmark specification",
        granted_permissions=[AgentPermission.READ],  # Missing WRITE permission
        project_id=proj_id,
    )

    agent.run_task(restricted_task, db)
    print(f"Restricted Task Status: {restricted_task.status.value}")
    assert restricted_task.status == AgentTaskStatus.WAITING_FOR_APPROVAL
    assert restricted_task.approval_token is not None
    print(f"Approval Token Generated: {restricted_task.approval_token}")

    # Approve restricted task
    restricted_task.granted_permissions.append(AgentPermission.WRITE)
    restricted_task.status = AgentTaskStatus.EXECUTING
    restricted_task.pending_tool_call = None
    restricted_task.approval_token = None
    agent.run_task(restricted_task, db)
    print(f"Approved Task Resumed Status: {restricted_task.status.value}")

    # 4. Main Real Gemini Execution Run
    print("\n--- Executing Real Autonomous Agent Workflow (Gemini + Atlas Tools) ---")
    start_time = time.time()

    real_task = AgentTask(
        goal=(
            "Create a disposable benchmark to test Python security vulnerability identification, "
            "generate and attach dataset tasks, validate dataset, run executions, evaluate, and generate a report."
        ),
        granted_permissions=[
            AgentPermission.READ,
            AgentPermission.WRITE,
            AgentPermission.EXECUTE,
            AgentPermission.PUBLISH,
        ],
        project_id=proj_id,
    )

    agent.run_task(real_task, db)
    elapsed_time = round(time.time() - start_time, 2)

    print("\n" + "=" * 80)
    print("                     EXECUTION RESULTS")
    print("=" * 80)
    print(f"Goal: '{real_task.goal}'")
    print(f"Final Task Status: {real_task.status.value}")
    print(f"Current Provider Used: {real_task.current_provider}")
    print(f"Total Steps: {real_task.step_count}")
    print(f"Total Tool Calls: {real_task.total_tool_calls}")
    print(f"Repair Attempts: {real_task.repair_attempts}")
    print(f"Total Execution Time: {elapsed_time}s")

    print("\n--- Sequence of Tool Calls & Gemini Decisions ---")
    for i, call in enumerate(real_task.tool_calls, 1):
        obs = next((o for o in real_task.observations if o.call_id == call.call_id), None)
        status_str = (
            "SUCCESS" if obs and obs.success else f"FAILED ({obs.error if obs else 'no obs'})"
        )
        print(f"Step {i}: Tool '{call.tool_name}' -> {status_str}")
        print(f"   Args: {json.dumps(call.arguments)}")
        if obs:
            print(f"   Output: {json.dumps(obs.output)[:120]}...")

    print("\n--- Final Plan State ---")
    for p in real_task.plan:
        print(f"  [{p.step_number}] ({p.status}) {p.description} -> {p.result_summary}")

    print("\n--- Final Summary / Response ---")
    if real_task.final_result:
        print(json.dumps(real_task.final_result, indent=2))
    elif real_task.error_detail:
        print(f"[ERROR DETAIL]: {real_task.error_detail}")

    print("\n--- Persisted DB Records Verification ---")
    bm_count = db.query(Benchmark).count()
    ds_count = db.query(Dataset).count()
    ex_count = db.query(Execution).count()
    print(f"Disposable Benchmarks in DB: {bm_count}")
    print(f"Disposable Datasets in DB: {ds_count}")
    print(f"Disposable Executions in DB: {ex_count}")

    # Cleanup test DB file
    db.close()
    engine.dispose()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print("\nCleaned up disposable database file.")
        except Exception as e:
            print(f"\nDisposable database cleanup note: {e}")


if __name__ == "__main__":
    main()
