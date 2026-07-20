# Benchmark Lifecycle & Domain Specification

This document defines the product behavior, business rules, and API contracts for Benchmark Authoring (Phase A). It serves as the single source of truth for the backend implementation of this milestone.

## 1. Lifecycle States

Benchmarks in Atlas follow a strict state machine defined by the `BenchmarkState` enum:

- **PROPOSAL**: Initial idea. Requires only a title, high-level objective, and owner. No structure required yet.
- **DESIGN**: The benchmark structure, dataset associations, metrics, and evaluation strategy are being designed.
- **DRAFT**: Implementation is largely complete but still editable. Iteration occurs here.
- **VALIDATION**: Automated validation is running (verifying schema, dataset links, required metadata, evaluation configuration).
- **REVIEW**: Passed validation and is awaiting human/admin approval.
- **PUBLISHED**: Immutable, versioned, and available for executions.
- **ARCHIVE**: Retired. Cannot accept new executions but remains available for historical reproducibility.

### State Transition Table

| From | Allowed To |
| :--- | :--- |
| **PROPOSAL** | DESIGN, ARCHIVE |
| **DESIGN** | DRAFT, ARCHIVE |
| **DRAFT** | VALIDATION, DESIGN, ARCHIVE |
| **VALIDATION** | REVIEW, DRAFT |
| **REVIEW** | PUBLISHED, DRAFT |
| **PUBLISHED** | ARCHIVE |
| **ARCHIVE** | *(none)* |

> [!WARNING]
> Invalid state transitions (e.g., jumping from `PROPOSAL` straight to `PUBLISHED`) must be rejected by the backend API.

## 2. Ownership & Permissions

- **Creation**: Any authenticated user within an organization can create a benchmark (starts in `PROPOSAL`). They become the `author`.
- **Editing**: Project members with `write` access and Organization Admins can edit unpublished versions (`PROPOSAL`, `DESIGN`, `DRAFT`).
- **Publishing**: Only Organization Admins or the `author` (if they have sufficient project permissions) can transition a benchmark from `REVIEW` to `PUBLISHED`.
- **Archiving**: Only Organization Admins or the `author` can archive a benchmark.

## 3. Versioning & Immutability

- **One Active Editable Version**: Atlas intentionally supports a single active editable version per benchmark. This avoids introducing Git-like branching semantics into the benchmark lifecycle. Collaborative editing occurs on the active draft, while published versions remain immutable snapshots. 
- **Immutability**: Once a benchmark enters the `PUBLISHED` state, its core configuration (dataset links, evaluation strategies, metrics) is **strictly immutable**. 
- **New Versions**: To make changes to a `PUBLISHED` benchmark, a new version must be created. The new version starts in `DRAFT` (or `DESIGN`).
- **Deletion**: Unpublished versions (`PROPOSAL`, `DESIGN`, `DRAFT`) can be soft-deleted. `PUBLISHED` and `ARCHIVED` versions cannot be deleted, only archived.

## 4. Dataset Binding

- **Specific Binding**: A benchmark version is always tied to a **specific dataset version**, not just the abstract dataset entity.
- **Multiple Datasets**: A single benchmark version can reference multiple datasets.
- **Version Independence**: Different versions of the same benchmark can reference different dataset versions.
- **Dataset Archival**: If a dataset version linked to a `PUBLISHED` benchmark is archived, the benchmark remains `PUBLISHED` and executable (archived datasets are read-only but still exist).

## 5. Validation Rules (for transitioning to VALIDATION/REVIEW)

Before a benchmark can successfully transition to `VALIDATION` and then to `REVIEW`/`PUBLISHED`, the following business rules must be met:
- **Datasets**: At least one valid dataset version must be linked.
- **Evaluators**: At least one evaluation strategy must be configured.
- **Metrics**: At least one scoring metric must be defined.
- **Taxonomy**: The benchmark must have at least one Capability and Category assigned.

## 6. Execution Rules

- **Published Only**: By default, only `PUBLISHED` benchmarks can accept production executions.
- **Private Executions**: `DRAFT` benchmarks can be executed privately by the author or project members for testing purposes. These executions are not indexed in global leaderboards.
- **Archived Executions**: `ARCHIVED` benchmarks cannot accept *new* executions, but historical executions against them remain accessible.
- **Default Version**: If an execution request specifies a benchmark ID without a version string, the backend defaults to the latest `PUBLISHED` version.

## 7. System Invariants

These rules must never be violated under any circumstances:
- A `PUBLISHED` benchmark is strictly immutable.
- A benchmark version always references immutable dataset versions.
- Every execution references exactly one benchmark version.
- Every evaluation references exactly one execution.
- Every report references exactly one evaluation.

## 8. Out of Scope

The following features are explicitly excluded from Phase A (Benchmark Authoring):
- Leaderboards
- Reports
- Global Search
- Analytics
- Python SDK
- CLI
- Frontend UI
