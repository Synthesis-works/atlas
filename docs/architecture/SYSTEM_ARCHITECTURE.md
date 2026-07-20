# Atlas System Architecture (Handbook)

## Overview
Atlas is an Evaluation Operating System designed to author, execute, evaluate, and report on the performance of models across standardized benchmarks. It is composed of highly decoupled subsystems communicating through well-defined APIs and sharing a unified, robust PostgreSQL foundation.

## High-Level System Map

```text
Atlas
├── Authoring (Planned)
├── Dataset (In Progress)
├── Execution (Closed)
├── Evaluation (Closed)
├── Reporting (Closed)
├── Frontend (Planned)
├── Authentication (Planned)
└── API Gateway (Planned)
```

## Subsystem Details

### 1. Database Foundation (v0.2)
- **Purpose:** Provide a centralized, transactional, and relational storage backbone.
- **Owner:** Platform/Infrastructure
- **Data Ownership:** Owns schema migrations (`alembic`) and the base SQLAlchemy models.
- **Invariants:** 
  - Strictly normalized schemas.
  - No domain logic embedded in the models.

### 2. Execution Core (v0.4 & v0.5)
- **Purpose:** Orchestrate the running of models against benchmarks via adapters (Local, Kubernetes, AWS Batch).
- **Owner:** Execution Engine Team
- **Inputs:** `BenchmarkVersion`, `TargetModel`, `ExecutionAdapter`
- **Outputs:** `AtlasRun`, `ModelOutput`, `Artifact`
- **Data Ownership:** Owns the lifecycle of a "Run" from PENDING to COMPLETED/FAILED.
- **Invariants:** Execution produces raw outputs but never evaluates them.

### 3. Evaluation Core (v0.6)
- **Purpose:** Score model outputs against defined strategies (Exact Match, LLM Judge, Scripts) and synthesize capability profiles.
- **Owner:** Evaluation Science Team
- **Inputs:** `ModelOutput`, `EvaluationStrategy`, `Judge`
- **Outputs:** `EvaluationResult`, `CapabilityProfile`, `CapabilityScore`
- **Data Ownership:** Owns the scoring and capability assessment.
- **Invariants:** Evaluation only acts on completed runs and never mutates execution state.

### 4. Reporting Core (v0.7)
- **Purpose:** Aggregate, analyze, and present data across Execution and Evaluation.
- **Owner:** Product/Analytics Team
- **Inputs:** All persisted data.
- **Outputs:** Leaderboards, Capability Dashboards, Trend Analysis, Data Exports (JSON/CSV).
- **Data Ownership:** Owns strictly no domain state. Minimal persistence for user views (Future: `SavedReport`).
- **Invariants:** Strictly read-only; never runs models or evaluations.

### 5. Dataset Service (v0.8 - In Progress)
- **Purpose:** Manage the ingestion, validation, versioning, cleaning, and publishing of evaluation datasets.
- **Owner:** Data Platform Team
- **Outputs:** Published `Dataset`, `DatasetVersion`, `Source`, `License`
- **Data Ownership:** Sole owner of dataset ingestion and lineage.
- **Invariants:** Dataset service is completely independent of Execution, Evaluation, and Reporting. It provides data for Authoring and Execution to consume.

### 6. Authoring Service (v0.9 - Planned)
- **Purpose:** Allow users to build benchmarks, tasks, test cases, and prompts using published datasets.
- **Dependencies:** Heavily relies on the Dataset Service.

### 7. Frontend, Auth, and API Gateway (Planned)
- To be designed post-backend completion (v1.0).

## Deployment & Lifecycle
- Each subsystem is structured as an independently deployable microservice, although currently co-located in a monorepo for cohesive database access.
- **Lifecycle:** Architecture -> Database -> Core Logic -> API -> Tests -> Freeze -> PR -> Merge -> Tag -> Close.
