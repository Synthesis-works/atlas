# Agent Handoff

Welcome to Project Atlas. This document is written specifically for future AI coding agents and human developers joining the project to quickly understand the context, architecture, and current state.

## Project Summary
- **What Atlas is**: A distributed execution and evaluation platform for large language models.
- **Current project goals**: Orchestrate complex LLM evaluation workflows synchronously and asynchronously with full observability and immutable versioning.
- **Overall architecture**: A clean, modular, event-driven backend. Unidirectional dependencies isolate core domain logic from execution engines.
- **Technology stack**: Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, Celery, Redis. Dependency management via `uv`.
- **Repository layout**: Monorepo-style splitting `apps` (entrypoints), `packages` (foundational logic), and `services` (business domains).

### Important Directories
- `apps/backend/`: FastAPI application routers and configurations.
- `apps/backend/worker/`: Celery task definitions and entrypoints.
- `packages/database/`: Core SQLAlchemy models, repository patterns, and Alembic migrations.
- `services/`: Domain logic divided by capability (`auth`, `execution`, `evaluation`, etc.).
- `docker/`: Dockerfiles.

## Current Infrastructure
- **Docker**: The canonical way to run the stack. Uses `docker-compose.yml` for dev and `docker-compose.prod.yml` for production.
- **Database**: PostgreSQL handles all relational storage. Initialized by Alembic on API startup.
- **Execution Service**: Dispatches generic compute tasks.
- **Workers**: Celery workers consuming from Redis. They execute benchmarks and LLM models.
- **Scheduler**: Celery Beat, enqueuing periodic tasks.
- **API**: FastAPI providing REST endpoints to the frontend and programmatic clients.
- **Configuration**: Uses `pydantic-settings` falling back to `.env`.
- **Environment variables**: `DATABASE_URL` and `CELERY_BROKER_URL` are most critical for infrastructure wiring.
- **Networking**: All services run in a standard bridge network defined by compose. Containers resolve each other via service name (e.g., `db`, `redis`).

## Development Workflow
- **Git workflow**: Feature branch workflow. 
- **Commit conventions**: Use atomic, logical commits. Never commit to `main` directly.
- **Dependency management**: 
  - **uv** is the canonical dependency resolver (`uv.lock` is tracked). Use `uv sync` to install exactly what is locked.
  - **Poetry** is installed in the Docker image as an optional developer convenience for running local scripts or managing virtual environments outside the primary `uv` pipeline. DO NOT use Poetry to alter `pyproject.toml` dependencies if it breaks `uv.lock`.
- **Build process**: Standard `pip install -e .` or `uv pip install -e .` during local testing, but Docker relies on `uv sync` for building layers securely.
- **Docker workflow**: Always bind mount `.:/app` in local development to preserve hot-reloading with Uvicorn.

## Major Work Completed
1. **Database foundation**: Established Alembic migrations and repository pattern.
2. **Execution service**: Designed the asynchronous celery orchestration and unidirectional event bus.
3. **Architecture audit**: A thorough review of system boundaries and readiness.
4. **Dockerization**: Rollout of multi-stage Dockerfiles, Compose files, and proper health checks.

## Current State
- **What currently works**: The base API, Celery worker infrastructure, database connections, and Docker wiring.
- **What is partially implemented**: The frontend (only a Next.js stub exists in `apps/web`).
- **What is missing**: Real LLM integrations (currently mocked).
- **What still needs validation**: A real runtime execution using Docker Engine on a host machine to verify Celery auto-discovery and migration execution.

## Known Issues
- **High**: No Docker validation has been performed yet natively. `docker compose up --build` must be run.
- **Medium**: `apps/web` exists but has no `package.json`, causing it to be stripped from Docker Compose until properly initialized.

## Future Work
- **Immediate**: Perform a complete Docker runtime validation.
- **Short term**: Initialize the Next.js frontend and reintegrate it into `docker-compose.yml`.
- **Long term**: Add robust external LLM providers and production logging/APM integrations.

## Important Files
- `pyproject.toml` / `uv.lock`: Dependency definitions.
- `docker-compose.yml`: The primary entry point for launching the system.
- `packages/database/alembic/env.py`: Controls database migration targeting (must read `DATABASE_URL`).
- `apps/backend/main.py`: FastAPI server initialization.

## Agent Guidelines
1. **Never modify `main` directly.** Always create and switch to a feature branch.
2. **Run validation before commits.** (e.g., `pytest`, `docker compose config`).
3. **Keep documentation updated.** Modify this file or `PROJECT_STATE.md` if architecture shifts.
4. **Never invent services.** Do not add non-existent paths to Docker or configs.
5. **Never assume runtime paths.** Always check if a config relies on absolute or relative paths.
