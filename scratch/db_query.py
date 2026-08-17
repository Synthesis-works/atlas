import os
import sys
import json

sys.path.insert(0, os.path.abspath("packages/database"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from atlas_db.core.config import config
from atlas_db.models.execution import Execution

sys.stdout.reconfigure(encoding="utf-8")

print("=== 1. DIRECT POSTGRESQL QUERY FOR EXECUTIONS ===")
engine = create_engine(config.database_url, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

try:
    all_executions = session.query(Execution).all()
    print(f"TOTAL EXECUTION ROWS IN POSTGRESQL: {len(all_executions)}\n")

    real_count = 0
    demo_count = 0

    for i, ex in enumerate(all_executions):
        cfg = ex.execution_config or {}
        is_verified = cfg.get("is_verified", False)
        source = cfg.get("source", "unknown")

        if is_verified or source == "real":
            real_count += 1
        else:
            demo_count += 1

        print(f"Row #{i + 1}: ID={ex.id}")
        print(f"  Target Model : {ex.target_model}")
        print(f"  Benchmark Ver: {ex.benchmark_version_id}")
        print(f"  Project ID   : {ex.project_id}")
        print(f"  Status       : {ex.status}")
        print(f"  Source       : {source} (is_verified={is_verified})")
        print(f"  Created At   : {ex.created_at}")
        print(f"  Config JSON  : {cfg}")
        print("-" * 60)

    print(f"\nSUMMARY: Real Runs = {real_count} | Demo Runs = {demo_count}")

finally:
    session.close()
