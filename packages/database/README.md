# Atlas Database Foundation

This package provides the core relational database foundation for Project Atlas, an AI Evaluation Operating System.

## Architecture

The database is built on **SQLAlchemy 2.0** and uses **PostgreSQL**.
Migrations are managed with **Alembic**.

We use the **Repository Pattern** (`atlas_db.repositories`) to abstract data access from business logic in the upper service layers.

### Subsystems

The database is cleanly separated into subsystems:
- **Core**: Organizations, Users, Projects, Configurations.
- **Dataset Registry**: Datasets, Versions, Sources, Licenses.
- **Benchmark Authoring**: Benchmarks, Lifecycles, Tasks, Test Cases, Prompts.
- **Execution Platform**: Execution Adapters, Evaluation Sessions, Atlas Runs, Model Outputs.
- **Evaluation Methodology**: Strategies, Judges, Evaluation Results, Capability Profiles.
- **Reporting & System**: Reports, Metrics, Audit Logs, Notifications.

### Usage

**Configuration:**
Uses `pydantic-settings` via environment variables:
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

**Dependencies:**
```python
from atlas_db.core.session import get_db, get_async_db
from atlas_db.repositories import benchmark_repo

# FastAPI dependency injection
@app.get("/benchmarks")
def list_benchmarks(db: Session = Depends(get_db)):
    pass
```

### Migrations

Initial migration has been generated. To apply migrations:
```bash
poetry run alembic upgrade head
```
