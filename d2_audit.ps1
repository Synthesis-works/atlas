$env:PYTHONPATH = "packages/database;packages;apps;services;."

echo "-- 1. Environment --" > final_proof.txt
uv --version >> final_proof.txt 2>&1
uv run python --version >> final_proof.txt 2>&1
uv run python -c "import sqlalchemy; print(sqlalchemy.__version__)" >> final_proof.txt 2>&1
uv run python -c "import alembic; print(alembic.__version__)" >> final_proof.txt 2>&1
uv run python -c "import psycopg2; print(psycopg2.__version__)" >> final_proof.txt 2>&1
uv run python -c "import pytest; print(pytest.__version__)" >> final_proof.txt 2>&1
uv run python -c "from packages.database.atlas_db.services.dataset_extraction import DatasetExtractionService; print('DatasetExtractionService OK')" >> final_proof.txt 2>&1
uv run pytest --version >> final_proof.txt 2>&1

echo "-- 2. Scope --" >> final_proof.txt
git status --short >> final_proof.txt
git diff --check >> final_proof.txt
git diff --stat >> final_proof.txt
git diff --name-only >> final_proof.txt

echo "-- 3. D2 Tests --" >> final_proof.txt
uv run pytest packages/database/tests -v >> final_proof.txt 2>&1

echo "-- 4. Full Regression --" >> final_proof.txt
uv run pytest -q -W default >> final_proof.txt 2>&1

echo "-- 5. PostgreSQL Integration --" >> final_proof.txt
uv run pytest packages/database/tests/test_d2_postgres_integration.py -v >> final_proof.txt 2>&1

echo "-- 6. Alembic State --" >> final_proof.txt
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/test_upgrade_safety"
uv run alembic current >> final_proof.txt 2>&1
uv run alembic heads >> final_proof.txt 2>&1
uv run alembic check >> final_proof.txt 2>&1

echo "-- 7. Fresh DB --" >> final_proof.txt
uv run python -c "import psycopg2; conn = psycopg2.connect('dbname=postgres user=postgres password=postgres host=localhost'); conn.autocommit = True; conn.cursor().execute('DROP DATABASE IF EXISTS verify_fresh'); conn.cursor().execute('CREATE DATABASE verify_fresh');"
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/verify_fresh"
uv run alembic upgrade head >> final_proof.txt 2>&1
uv run alembic check >> final_proof.txt 2>&1

echo "-- 8. Legacy DB --" >> final_proof.txt
uv run python -c "import psycopg2; conn = psycopg2.connect('dbname=postgres user=postgres password=postgres host=localhost'); conn.autocommit = True; conn.cursor().execute('DROP DATABASE IF EXISTS verify_legacy'); conn.cursor().execute('CREATE DATABASE verify_legacy');"
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/verify_legacy"
uv run alembic upgrade b8fe9ea13c79 >> final_proof.txt 2>&1
uv run python insert_test_data.py >> final_proof.txt 2>&1
uv run alembic upgrade head >> final_proof.txt 2>&1
uv run alembic check >> final_proof.txt 2>&1

echo "-- 9. Dependencies --" >> final_proof.txt
git grep -n "apps.backend.worker" packages/database packages/datasets >> final_proof.txt 2>&1 || echo "None found." >> final_proof.txt
git grep -n "PromptResolver" packages/database/atlas_db/services/dataset_extraction.py >> final_proof.txt 2>&1 || echo "None found." >> final_proof.txt

echo "-- 10. Metadata Security --" >> final_proof.txt
uv run pytest packages/database/tests/test_d2_suite.py -k "metadata or leakage" -v >> final_proof.txt 2>&1

echo "-- 11. D2 E2E --" >> final_proof.txt
uv run pytest packages/database/tests/test_d2_suite.py -k "humaneval or mbpp" -v >> final_proof.txt 2>&1
