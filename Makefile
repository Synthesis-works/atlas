.PHONY: db-up db-down db-migrate db-upgrade db-downgrade db-seed

db-up:
	docker compose up -d db

db-down:
	docker compose down

db-migrate:
	cd packages/database && poetry run alembic revision --autogenerate -m "$(m)"

db-upgrade:
	cd packages/database && poetry run alembic upgrade head

db-downgrade:
	cd packages/database && poetry run alembic downgrade -1

db-seed:
	cd packages/database && poetry run python scripts/seed.py
