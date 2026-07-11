# Database Foundation Changelog (Atlas V1)

## Files Modified
* `packages/database/atlas_db/core/base.py`: Applied `naming_convention` to `MetaData` to enforce deterministic constraint and index naming.
* `packages/database/atlas_db/models/core.py`: Fixed `chk_configuration_scope` check constraint to validate against uppercase `ENUM` serialization natively matched by Alembic.
* `packages/database/alembic/versions/4007056c9559_initial_migration.py`: Applied offline regex patch to assign proper naming convention constraint names (PKs, FKs, UQs) to the initial migration schema.
* `packages/database/tests/conftest.py`: Monkey-patched `SQLiteTypeCompiler` to elegantly map Postgres-specific `JSONB` and `ENUM` types to compatible SQLite types for in-memory testing.
* `packages/database/atlas_db/repositories/base.py`: Overhauled to implement automatic soft-delete filtering via `archived_at`, defaulting `.delete()` to archive, and updated legacy SQLAlchemy `.get()` syntax.

## Files Created
* `packages/database/atlas_db/repositories/core.py`: Concrete repositories for `Organization`, `User`, `Project`, `Configuration`, `ConfigurationVersion`.
* `packages/database/atlas_db/repositories/dataset.py`: Concrete repositories for `Dataset`, `DatasetVersion`, `DatasetRegistry`, `DatasetSource`, `DatasetLicense`.
* `packages/database/atlas_db/repositories/authoring.py`: Concrete repositories for `Benchmark`, `BenchmarkVersion`, `BenchmarkLifecycle`, `BenchmarkCategory`, `Capability`.
* `packages/database/atlas_db/repositories/tasks.py`: Concrete repositories for `Task`, `Prompt`, `TestCase`, `Constraint`, `EvaluationRule`.
* `packages/database/atlas_db/repositories/execution.py`: Concrete repositories for `ExecutionAdapter`, `ExecutionAdapterVersion`, `EvaluationSession`, `AtlasRun`, `ModelOutput`, `Artifact`.
* `packages/database/atlas_db/repositories/evaluation.py`: Concrete repositories for `EvaluationStrategy`, `EvaluationStrategyVersion`, `Judge`, `EvaluationResult`, `CapabilityProfile`, `CapabilityScore`.
* `packages/database/atlas_db/repositories/reporting.py`: Concrete repositories for `Report`, `ReportVersion`, `ReportMetric`.
* `packages/database/atlas_db/repositories/system.py`: Concrete repositories for `AuditLog`, `Notification`.
* `packages/database/atlas_db/repositories/__init__.py`: Centralized module exports for all repository classes (singletons removed in favor of explicit session passing).

## Architectural Decisions
1. **Implemented Naming Conventions via `Base.metadata`** 
   * *Rationale*: Ensures deterministic constraint naming by SQLAlchemy and Alembic, avoiding duplicate migration creation issues in PostgreSQL.
2. **Transparent Repository-level Soft Deletes** 
   * *Rationale*: Preserves historical auditability without forcing application logic to handle complex soft-delete lifecycle conditionals.
3. **Offline Migration Patching** 
   * *Rationale*: Enforced the architectural naming conventions on the initial migration without requiring a live Postgres instance on a host restricting Docker.
4. **`SQLiteTypeCompiler` Mocking** 
   * *Rationale*: Enables seamless, zero-dependency local testing of Postgres-specific types (`JSONB`/`ENUM`) by dynamically bridging unsupported mappings to SQLite.
