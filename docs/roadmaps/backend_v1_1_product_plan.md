# Backend v1.1 Product Plan Roadmap

Atlas backend development follows a workflow-oriented lifecycle, mapped into 5 sequential phases.

> [!IMPORTANT]
> **Specification-First Development**
> Before any implementation begins for a phase, a corresponding product specification document must be created and agreed upon. This specification serves as the domain contract (e.g., `benchmark_lifecycle.md`).

## Phase A: Benchmark Authoring (Milestone 1)
**Goal**: Everything required for a user to author, validate, and publish a benchmark. Datasets are handled here as a dependency for benchmark creation.
**Deliverables**:
- **Product Specification**: `benchmark_lifecycle.md`
- Dataset Lifecycle (CRUD, versioning, metadata, validation)
- Benchmark CRUD & Versioning
- Publishing & Archiving workflows
- Permissions & Validation rules

## Phase B: Execution APIs (Milestone 2)
**Goal**: Users can trigger and monitor executions against published benchmarks.
**Deliverables**:
- **Product Specification**: `execution_lifecycle.md`
- Execution queueing (`POST /executions`)
- Status and logging APIs (`GET /status`, `GET /logs`)
- Lifecycle actions (`POST /cancel`, retry operations)

## Phase C: Evaluation & Reports (Milestone 3)
**Goal**: Expose evaluation scores, metrics, and report generation for completed executions.
**Deliverables**:
- **Product Specification**: `evaluation_contract.md`, `reporting_contract.md` (To be created after Phase B specification)
- Result fetching (`GET /evaluations`)
- Report retrieval and export APIs (`GET /reports`, `GET /summary`, `GET /metrics`)

## Phase D: Discovery (Milestone 4)
**Goal**: Make the platform pleasant to use with comprehensive search and filtering capabilities.
**Deliverables**:
- Global and entity-specific search APIs
- Filtering, sorting, and pagination across all lists
- History and recent access APIs

## Phase E: Leaderboards (Milestone 5)
**Goal**: Build the primary engagement feature: model rankings and capability profiles.
**Deliverables**:
- **Product Specification**: `leaderboard_spec.md`
- Data models for materialized leaderboards
- APIs for model rankings, capability profiles, historical trends, and comparisons
