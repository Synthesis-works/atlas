$env:PYTHONPATH="packages/database;packages;apps;services;."

echo "1. git status --short" > zero_trust_results.txt
git status --short >> zero_trust_results.txt

echo "`n2. git diff --stat" >> zero_trust_results.txt
git diff --stat >> zero_trust_results.txt

echo "`n3. git diff --check" >> zero_trust_results.txt
git diff --check >> zero_trust_results.txt

echo "`n4. uv run pytest -q" >> zero_trust_results.txt
uv run pytest -q >> zero_trust_results.txt 2>&1

echo "`n5. D2 PostgreSQL pytest suite" >> zero_trust_results.txt
uv run pytest packages/database/tests/test_d2_postgres_integration.py -v >> zero_trust_results.txt 2>&1

echo "`n6. uv run alembic current" >> zero_trust_results.txt
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/test_upgrade_safety"
uv run alembic -c packages/database/alembic.ini current >> zero_trust_results.txt 2>&1

echo "`n7. uv run alembic heads" >> zero_trust_results.txt
uv run alembic -c packages/database/alembic.ini heads >> zero_trust_results.txt 2>&1

echo "`n8. uv run alembic check" >> zero_trust_results.txt
uv run alembic -c packages/database/alembic.ini check >> zero_trust_results.txt 2>&1

echo "`n9. fresh database -> alembic upgrade head" >> zero_trust_results.txt
uv run python -c "import psycopg2; conn = psycopg2.connect('dbname=postgres user=postgres password=postgres host=localhost'); conn.autocommit = True; conn.cursor().execute('DROP DATABASE IF EXISTS verify_fresh'); conn.cursor().execute('CREATE DATABASE verify_fresh');"
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/verify_fresh"
uv run alembic -c packages/database/alembic.ini upgrade head >> zero_trust_results.txt 2>&1

echo "`n10. D1.5 revision -> alembic upgrade head" >> zero_trust_results.txt
uv run python -c "import psycopg2; conn = psycopg2.connect('dbname=postgres user=postgres password=postgres host=localhost'); conn.autocommit = True; conn.cursor().execute('DROP DATABASE IF EXISTS verify_legacy'); conn.cursor().execute('CREATE DATABASE verify_legacy');"
$env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/verify_legacy"
uv run alembic -c packages/database/alembic.ini upgrade b8fe9ea13c79 >> zero_trust_results.txt 2>&1
uv run python insert_test_data.py >> zero_trust_results.txt 2>&1
uv run alembic -c packages/database/alembic.ini upgrade head >> zero_trust_results.txt 2>&1
uv run alembic -c packages/database/alembic.ini check >> zero_trust_results.txt 2>&1

echo "`n11. SQLAlchemy import" >> zero_trust_results.txt
uv run python -c "import sqlalchemy; print(sqlalchemy.__version__)" >> zero_trust_results.txt 2>&1

echo "`n12. Alembic import" >> zero_trust_results.txt
uv run python -c "import alembic; print(alembic.__version__)" >> zero_trust_results.txt 2>&1

echo "`n13. psycopg2 import" >> zero_trust_results.txt
uv run python -c "import psycopg2; print(psycopg2.__version__)" >> zero_trust_results.txt 2>&1

echo "`n14. pytest import" >> zero_trust_results.txt
uv run python -c "import pytest; print(pytest.__version__)" >> zero_trust_results.txt 2>&1
