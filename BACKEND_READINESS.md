# Backend Readiness

## What is ready?
- **Data Layer:** SQLAlchemy models, Alembic migrations, and repositories are fully stable and thoroughly separated by subsystem domains.
- **Business Logic:** Execution loops, metric extraction pipelines, LLM interfaces, and dataset processing pipelines are implemented as stable python `packages/`.
- **Infrastructure:** Centralized configuration, logging, and exception hierarchies are established. CI/CD tooling (`ruff`, `mypy`, `pytest`) is configured.

## What is missing?
- **Unified Gateway:** While the `dataset` and `report` services expose FastAPI routers, the overarching `Backend API` that routes requests for authoring, execution, and evaluation is missing.
- **Authentication:** There is currently no `users` table context or JWT validation middleware. Downstream services assume a trusting environment.

## What should Backend (v1.0) implement first?
1. Create `apps/backend/main.py` as the unified FastAPI application.
2. Integrate the existing FastAPI routers (e.g. from `services/dataset` and `services/report`) into the unified app.
3. Expose REST endpoints that hook into the `packages/orchestrator` and `packages/evaluation` pipelines to trigger experiments.
4. Add global exception handlers leveraging `packages.core.exceptions.AtlasException`.
