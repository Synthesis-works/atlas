# Atlas Backend Product Audit

## Implemented Features

### 1. Database Foundation
- **Evidence**: `packages/database/atlas_db/models/` contains comprehensive models for:
  - **Benchmarks**: `authoring.py` defines `Benchmark`, `BenchmarkCategory`, `Capability`, `BenchmarkLifecycle`, `BenchmarkVersion`.
  - **Datasets**: `dataset.py` defines `Dataset`, `DatasetVersion`, `DatasetRegistry`, `DatasetSource`, `DatasetLicense`.
  - **Executions**: `execution.py` defines `EvaluationSession`, `AtlasRun`, `ExecutionAdapter`, `ModelOutput`, `Artifact`.
  - **Evaluations**: `evaluation.py` defines `EvaluationStrategy`, `Judge`, `EvaluationResult`, `CapabilityProfile`.
  - **Reporting**: `reporting.py` defines `Report`, `ReportVersion`, `ReportMetric`.

### 2. Basic Project and Organization APIs
- **Evidence**: `apps/backend/routers/projects.py` and `apps/backend/routers/organizations.py` implement CRUD for projects and organizations. `apps/backend/main.py` explicitly mounts these routers under `/api/v1`.

### 3. Core Orchestration Engine
- **Evidence**: `packages/orchestrator/atlas_orchestrator.py` and `state_manager.py` demonstrate that the core internal execution engine exists for orchestrating runs.

---

## Partially Implemented Features

### 1. Dataset Management
- **Evidence**: `apps/backend/routers/datasets.py` includes basic endpoints for `list_datasets`, `create_dataset`, and `get_dataset`.
- **Details**: Missing versioning operations (the `DatasetVersion` model exists but is unexposed), update, delete, validation, import/export APIs, and search/filtering APIs.

---

## Missing Features

### 1. Benchmark Management APIs
- **Evidence**: There is no `apps/backend/routers/benchmarks.py` or any benchmark-related endpoints mounted in `apps/backend/main.py`, despite models existing in `packages/database/atlas_db/models/authoring.py`. CRUD, versioning, publishing, archiving, and search are missing.

### 2. Execution APIs
- **Evidence**: While `packages/orchestrator` and execution DB models exist, there are no endpoints in `apps/backend/routers/` to trigger an execution, queue runs, check status, cancel, retry, or fetch logs/history.

### 3. Evaluation APIs
- **Evidence**: No endpoints exist in `apps/backend/routers/` to fetch evaluation results, manage evaluation strategies, configure judges, or retrieve scores, despite models existing in `evaluation.py`.

### 4. Reporting APIs
- **Evidence**: No endpoints in `apps/backend/routers/` for report generation, retrieval, or export. `reporting.py` DB models remain internal.

### 5. Leaderboard Capabilities
- **Evidence**: No materialized leaderboard or ranking database models exist (only `CapabilityProfile` and `CapabilityScore`). There are no leaderboard routers or APIs for historical rankings, model comparison, or capability rankings in `apps/backend/routers/`.

### 6. Search Capabilities
- **Evidence**: Global search routers are absent. The existing routers only expose basic `limit`/`offset` pagination, lacking robust search or filtering across projects, benchmarks, datasets, reports, or executions.

---

## Nice-to-have Features

- **Public Python SDK / CLI**: Once the public API surface is complete, a well-typed Python SDK or CLI tool would drastically improve external consumption and developer usability.
- **Real-time Execution Status via WebSockets**: Implementing WebSockets for real-time execution status streams (rather than polling) for frontend and CLI consumers.
