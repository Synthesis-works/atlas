# Changelog

All notable changes to Project Atlas will be documented in this file.

## [v0.4-execution-core] - 2026-07-12
### Added
- **Execution Service Core Architecture**: Designed and implemented the vertical slices for the Execution Engine.
- **Worker Management**: Established `ExecutionWorker` models with robust telemetry (CPU/RAM/GPU, active load, region, hardware info). Implemented `RegisterWorkerCommand` and `HeartbeatWorkerCommand` logic.
- **Execution State Machines**: Implemented state transitions for Runs, Tasks, and Workers managed strictly by dedicated Controllers.
- **Task Ownership & Claims**: Built atomic task claiming mechanism utilizing pessimistic locking (`SKIP LOCKED`) to prevent race conditions in distributed worker clusters.
- **Event Sourcing**: Created `RunEvent` model and `EventPublisher` interface. All lifecycle transitions generate chronological, trace-level events tracking `atlas_run_id`, `atlas_task_id`, and `execution_worker_id`.
- **MVP Demo**: Built `execution_demo.py` showcasing self-contained, end-to-end execution loop including happy paths, double-claim preventions, and imposter verification.
- **Architectural Documentation**: Added `INVARIANTS.md`, `ARCHITECTURE_DECISIONS.md`, `DATABASE_INVARIANTS.md`, `STATE_MACHINE_REFERENCE.md`, and `SYSTEM_BOUNDARIES.md` as the "memory" of the execution core.

### Changed
- Expanded `RunStatus` with `VALIDATING` and `ABORTING`.
- Migrated API layer paradigms from bloated CRUD routers to strict Command Pattern execution (e.g., `CreateRunCommand`, `ClaimTasksCommand`).
- Track progress statistics (`total_tasks`, `completed_tasks`, etc.) directly on `AtlasRun` for O(1) reads instead of live aggregation.

## [v0.3-database-foundation]
### Added
- Foundation Schema for Atlas across Domains (Core, Datasets, Authoring, Execution).
- Alembic tracking and declarative SQLAlchemy configuration.

## [v0.2-benchmark-framework]
### Added
- Benchmark modeling and lifecycle architecture.

## [v0.1-architecture]
### Added
- Initial project layout and structure definition.
