# Agent and AI Guidelines

Welcome to Project Atlas. This document defines the engineering standards, workflows, and philosophical rules that all human developers and autonomous AI agents MUST follow when modifying this repository.

Many AI coding tools natively read files like this one at the repository root. Always assume these rules are strictly enforced.

## 1. Project Philosophy
- **Immutability**: Core domain models (Datasets, Benchmarks) must maintain strict versioning and reproducibility.
- **Unidirectional Dependencies**: Evaluation logic depends on Execution logic, never the reverse.
- **Observability First**: All tasks must generate robust telemetry (structured logs, tracing IDs, event bus emissions).

## 2. Coding Standards
- Language: Python 3.11+.
- Formatting: `ruff` (Black-compatible style, 100 char line limit).
- Type Hinting: Strict MyPy enforcement is required.
- Architecture: Repository Pattern for data access, cleanly decoupled from FastAPI routes and Celery workers.

## 3. Git Workflow
- **Never modify `main` directly.** All work must occur on dedicated feature branches.
- **Branch naming**: Use descriptive, lowercase, dash-separated names (e.g., `feature/docker-rollout`, `fix/redis-timeout`).
- **Commit conventions**: Use standard conventional commits (e.g., `feat:`, `fix:`, `docs:`, `build:`). Commits should be atomic and logical. Do not squash without cause.

## 4. Dependency Management
- **Canonical Manager**: `uv` and its `uv.lock` file are the definitive source of truth.
- **Optional Manager**: Poetry is permitted solely for developer convenience (local virtual environments, running custom scripts), but must NEVER overwrite or conflict with `uv.lock`.
- **Modifying Dependencies**: When adding dependencies to `pyproject.toml`, you must regenerate `uv.lock` safely.

## 5. Docker Workflow
- Always prioritize using existing Dockerfiles (`docker/backend/Dockerfile`).
- Keep images small via multi-stage builds.
- Execute runtime layers as a non-root user (`atlas`).
- Health checks must remain functioning and valid.
- `docker-compose.yml` is strictly for local dev (bind-mounting source code). `docker-compose.prod.yml` uses immutable built images. Maintain parity between both environments.

## 6. Architecture Principles
- Ensure new API routes are fully decoupled from Database schemas using Pydantic Models (Schemas).
- Background operations must be routed through the `EventBus` to the Celery workers rather than executed synchronously on the FastAPI thread.

## 7. Definition of Done
- Implementation fulfills the prompt entirely.
- New dependencies are recorded cleanly in `pyproject.toml` / `uv.lock`.
- Docker containers successfully build and pass health checks.
- Documentation has been updated to reflect architectural or config changes.
- Branch pushed cleanly to remote and ready for Pull Request.

## 8. Pre-PR Runtime Checklist
Refer strictly to [docs/RUNTIME_CHECKLIST.md](docs/RUNTIME_CHECKLIST.md) before concluding an implementation sprint.

## 9. Required Reading for Future Agents
Before proposing or writing any code, you must read:
1. `docs/AGENT_HANDOFF.md`
2. `docs/PROJECT_STATE.md`
3. `docs/IMPLEMENTATION_HISTORY.md`
4. `docs/docker_setup.md`

If documentation conflicts with source code, identify the conflict, explain it, and propose a resolution before acting blindly.

> **Migration Policy:** Once a migration has been committed to `main`, treat it as immutable unless it is the latest unpublished migration. Fix forward by creating new migrations whenever possible. Editing historical migrations should only be done when they have never been deployed outside local development.  

> [!WARNING]
> During the Dockerization effort (July 2026), migrations `3a1cf533642c` and `2256bd2b7c2c` were historically rewritten to fix a fatal dependency collision before the first production deployment. Do not attempt to revert these fixes.