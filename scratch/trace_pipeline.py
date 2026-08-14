import os
import sys
import json
import uuid

sys.path.insert(0, os.path.abspath("packages/database"))
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from atlas_db.core.config import config
from atlas_db.models.execution import Execution
from atlas_db.models.authoring import BenchmarkVersion, Benchmark

sys.stdout.reconfigure(encoding='utf-8')

print("=== 1. POSTGRESQL DATABASE INSPECTION ===")
engine = create_engine(config.database_url, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Query all executions
    all_executions = session.query(Execution).all()
    print(f"Total execution rows in database: {len(all_executions)}")
    
    real_executions = []
    for ex in all_executions:
        cfg = ex.execution_config or {}
        is_verified = cfg.get("is_verified", False)
        source = cfg.get("source", "")
        if is_verified or source == "real":
            real_executions.append(ex)

    print(f"Executions with is_verified=true or source='real': {len(real_executions)}\n")

    for ex in all_executions:
        cfg = ex.execution_config or {}
        print(f"ID: {ex.id}")
        print(f"  Target Model: {ex.target_model}")
        print(f"  Benchmark Version ID: {ex.benchmark_version_id}")
        print(f"  Project ID: {ex.project_id}")
        print(f"  Status: {ex.status}")
        print(f"  Created At: {ex.created_at}")
        print(f"  Config: {cfg}")
        print("-" * 50)
finally:
    session.close()

print("\n=== 2. FASTAPI BACKEND GET /api/v1/executions API TEST ===")
from fastapi.testclient import TestClient
from apps.backend.main import app

client = TestClient(app)
response = client.get("/api/v1/executions")
print(f"HTTP Status Code: {response.status_code}")
try:
    data = response.json()
    print("API JSON Output Snippet:")
    print(json.dumps(data, indent=2)[:2000])
except Exception as e:
    print(f"Failed to parse JSON: {e}")
