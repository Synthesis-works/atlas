# Platform Changelog (v0.9-platform-review)

## Deleted
- Removed 16+ empty `.gitkeep` directories across `packages/` (e.g., `ui`, `adapters`, `logger`, `config`) and `services/` (e.g., `user`, `project`, `storage`, `execution-service`). Reason: Eliminating ghost packages and reducing cognitive overhead.
- Removed duplicate `PaginatedHistoryResponseDTO`, `SystemHealthDTO`, and `VersionInfoDTO` from `services/report/models/dtos.py`.

## Added
- `packages/core/config.py`: Centralized `pydantic-settings`.
- `packages/core/logger.py`: Standardized python logging configuration.
- `packages/core/exceptions.py`: Base domain exceptions (`AtlasException`, `ResourceNotFoundError`, `ValidationError`).
- `packages/core/models/pagination.py`: Generic `PaginatedResponseDTO[T]`.
- `packages/core/models/health.py`: Unified `SystemHealthDTO` and `VersionInfoDTO`.
- `pyproject.toml`: Configured Ruff, Pytest, Mypy, and project dependencies.
- `.env.example`: Template for environment variables.
- `.github/workflows/test.yml`: Basic CI/CD pipeline verifying code formatting and tests.

## Modified
- `services/report/models/dtos.py`: Refactored to import and inherit from `packages.core.models.pagination.PaginatedResponseDTO` and `packages.core.models.health`.
- `ROADMAP.md`: Transitioned roadmap from platform milestones to product milestones.
