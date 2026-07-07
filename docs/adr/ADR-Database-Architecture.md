# ADR: Database Architecture for Project Atlas

**Status**: Accepted  
**Context**: Project Atlas requires a highly normalized, scalable, and versioned database to support the full AI Evaluation lifecycle (Benchmark Authoring -> Execution -> Evaluation -> Capability Profiling -> Reporting).

## Decision

We will use **PostgreSQL**, **SQLAlchemy 2.0**, and **Alembic**, employing the **Repository Pattern** for data access abstraction. 

### Key Architectural Choices:

1. **Normalization over JSON**: We heavily utilize normalized relational tables (e.g., `Task`, `TestCase`, `CapabilityScore`, `BenchmarkCategoryLink`) rather than storing large JSON blobs. `JSONB` is strictly reserved for arbitrary semi-structured data like `Configuration.value`, `EvaluationResult.raw_measurements`, or `AuditLog.changes`.
2. **Version Everything**: All major entities (Benchmarks, Datasets, Configurations, Execution Adapters, Reports, Evaluation Strategies) implement a `[Entity] -> [Entity]Version` pattern to ensure reproducibility of past evaluations.
3. **Execution Pipeline Model**: We model execution as `EvaluationSession -> AtlasRun -> ModelOutput -> EvaluationResult`. This accurately represents the state of the AI Evaluation Operating System rather than a generic CRUD app.
4. **Optimistic Concurrency Control**: We implement a `version_number` column on mutable entities to prevent race conditions during distributed updates.
5. **UUID Primary Keys**: Used universally to allow for disconnected data creation and easier distributed system synchronization.
6. **Auditability & Traceability**: All aggregate roots implement a standard `BaseMixin` containing `created_at`, `updated_at`, `created_by_id`, `updated_by_id`, and `archived_at` (for soft deletes). A dedicated `AuditLog` table tracks fine-grained entity changes.

## Consequences

**Positive:**
- Enforces strict data integrity via PostgreSQL constraints and enums.
- The schema faithfully represents the engineering architecture, enabling smooth development of backend services without fighting the DB.
- Future-proofed against marketplace, billing, and organizational multi-tenancy requirements via the `Organization` scoping.

**Negative:**
- The high degree of normalization and versioning tables means some queries will require complex JOINs, necessitating careful indexing (which has been implemented).
- The repository pattern introduces a slight boilerplate overhead but is outweighed by the decoupling benefits.
