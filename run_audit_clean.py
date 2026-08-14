import subprocess
import json
import os

checks = {}
env = os.environ.copy()
env["PYTHONPATH"] = "packages/database;packages;apps;services;."

p = subprocess.run(["uv", "run", "pytest", "packages/database/tests", "-v", "--tb=short"], text=True, capture_output=True, env=env)
checks['pytest_out'] = p.stdout
checks['pytest_code'] = p.returncode

a = subprocess.run(["uv", "run", "alembic", "-c", "packages/database/alembic.ini", "check"], text=True, capture_output=True)
checks['alembic'] = a.stdout
checks['alembic_code'] = a.returncode

g = subprocess.run(["git", "diff", "--stat"], text=True, capture_output=True)
checks['git_diff'] = g.stdout

d = subprocess.run(["git", "grep", "apps.backend.worker", "packages/database/"], text=True, capture_output=True)
checks['deps'] = d.stdout

with open("audit_clean.json", "w", encoding="utf-8") as f:
    json.dump(checks, f, indent=2)
