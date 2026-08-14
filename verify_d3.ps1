$env:PYTHONPATH = "packages/database;packages;apps;services;."

echo "--- SYNC & STATUS ---"
uv sync --extra dev
uv lock --check
uv run python -c "import sqlalchemy, alembic, pytest, psycopg2; print('core imports OK')"

echo "--- REGRESSION ---"
uv run pytest -q

echo "--- POSTGRES D2 ---"
uv run pytest packages/database/tests/test_d2_postgres_integration.py -v

echo "--- D3 EXPORTERS ---"
uv run pytest packages/datasets/tests/test_d3_exporters.py -v
uv run pytest packages/datasets/tests/test_d3_export_service.py -v

echo "--- ALEMBIC ---"
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/verify_fresh"
uv run alembic check
uv run alembic current
uv run alembic heads

echo "--- GIT BOUNDARY ---"
git diff --check
git status --short
git diff --stat

echo "--- EXACT MODIFICATIONS ---"
git diff -- pyproject.toml packages/datasets/models.py tests/execution/test_persistence.py tests/api/test_dataset_contract.py

echo "--- ARCH BOUNDARY EXPORTER ---"
git grep -n "DatasetExporter\|DatasetExportService\|BaseTrainingArtifactStore" packages/datasets

echo "--- LEAKAGE CHECK ---"
git grep -n "apps.backend.worker\|PromptResolver\|celery" packages/datasets/exporters packages/datasets/services packages/datasets/infrastructure
