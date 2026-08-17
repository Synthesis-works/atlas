$env:PYTHONPATH = "packages/database;packages;apps;services;."

echo "-- PyTest --" > proof.txt
uv run pytest -q >> proof.txt 2>&1

echo "-- Alembic Check --" >> proof.txt
uv run alembic -c packages/database/alembic.ini check >> proof.txt 2>&1

echo "-- Git Scope --" >> proof.txt
git status --short >> proof.txt
git diff --name-only >> proof.txt

echo "-- Legacy Upgrade --" >> proof.txt
uv run python -c "import psycopg2; conn = psycopg2.connect('dbname=postgres user=postgres password=postgres host=localhost'); conn.autocommit = True; conn.cursor().execute('DROP DATABASE IF EXISTS prove_legacy'); conn.cursor().execute('CREATE DATABASE prove_legacy');"
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/prove_legacy"
uv run alembic -c packages/database/alembic.ini upgrade b8fe9ea13c79 >> proof.txt 2>&1
uv run python insert_test_data.py >> proof.txt 2>&1
uv run alembic -c packages/database/alembic.ini upgrade head >> proof.txt 2>&1
uv run alembic -c packages/database/alembic.ini check >> proof.txt 2>&1

echo "-- DONE --" >> proof.txt
