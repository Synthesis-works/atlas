$env:PYTHONPATH = "packages/database;packages;apps;services;."

echo "-- 1. Scope --" > d3_proof.txt
git status --short >> d3_proof.txt
git diff --stat >> d3_proof.txt
git diff --check >> d3_proof.txt

echo "-- 2. Lockfile --" >> d3_proof.txt
uv lock --check >> d3_proof.txt 2>&1

echo "-- 3. Full Regression --" >> d3_proof.txt
uv run pytest -q >> d3_proof.txt 2>&1

echo "-- 4. Alembic Check --" >> d3_proof.txt
# Requires postgres fresh db setup if not local
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/verify_fresh"
uv run alembic check >> d3_proof.txt 2>&1

echo "-- 5. D2 PostgreSQL --" >> d3_proof.txt
uv run pytest packages/database/tests/test_d2_postgres_integration.py -v >> d3_proof.txt 2>&1

echo "-- 6. D3 Exporters --" >> d3_proof.txt
uv run pytest packages/datasets/tests/test_d3_exporters.py -v >> d3_proof.txt 2>&1

echo "-- 7. D3 Services --" >> d3_proof.txt
uv run pytest packages/datasets/tests/test_d3_export_service.py -v >> d3_proof.txt 2>&1

echo "-- 8. PyProject Diff --" >> d3_proof.txt
git diff -- pyproject.toml >> d3_proof.txt

echo "-- 9. D3 Diff --" >> d3_proof.txt
git diff -- packages/datasets/exporters/ >> d3_proof.txt
git diff -- packages/datasets/services/ >> d3_proof.txt
git diff -- packages/datasets/infrastructure/ >> d3_proof.txt
