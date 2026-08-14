import os
import sys
import json

sys.path.insert(0, os.path.abspath("packages/database"))
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from apps.backend.main import app

sys.stdout.reconfigure(encoding='utf-8')

client = TestClient(app)

print("=== CALLING GET /api/v1/executions VIA FASTAPI TESTCLIENT ===")
response = client.get("/api/v1/executions")
print(f"HTTP Status: {response.status_code}")

if response.status_code == 200:
    res_data = response.json()
    items = res_data.get("data", {}).get("items", []) if isinstance(res_data, dict) and "data" in res_data else (res_data.get("items", []) if isinstance(res_data, dict) else res_data)
    
    print(f"Total executions returned by API: {len(items)}\n")
    
    qwen_items = [item for item in items if "qwen" in str(item.get("target_model", "")).lower()]
    real_items = [item for item in items if item.get("execution_config", {}).get("is_verified") or item.get("execution_config", {}).get("source") == "real"]

    print(f"Qwen executions in API response: {len(qwen_items)}")
    print(f"Verified/Real executions in API response: {len(real_items)}\n")

    print("--- SAMPLE REAL/VERIFIED RUNS RETURNED BY GET /api/v1/executions ---")
    for item in real_items[:10]:
        print(f"ID: {item.get('id')}")
        print(f"  Target Model : {item.get('target_model')}")
        print(f"  Benchmark Ver: {item.get('benchmark_version_id')}")
        print(f"  Status       : {item.get('status')}")
        print(f"  Config       : {item.get('execution_config')}")
        print("-" * 50)
else:
    print(f"Error response: {response.text}")
