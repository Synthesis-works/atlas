# Database Invariants

This document outlines the hard rules that must always hold true for the PostgreSQL database foundation of Atlas.

## Schema & Integrity
1. **Canonical Truth**: The database is the single source of truth for all system states. Caching layers (e.g., Redis) may exist for read optimization but never for state ownership.
2. **Deterministic Constraint Naming**: All foreign keys, unique constraints, and indexes must follow the deterministic naming convention defined by SQLAlchemy's `MetaData` naming convention (e.g. `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`).
3. **No Soft Deletes**: We do not use soft deletes. If a record needs to be retained for history, it should be versioned or event-sourced.

## Versioning & Mutability
1. **Immutable Benchmark Assets**: Once a `BenchmarkVersion` or `DatasetVersion` is used in a Run, its associated records cannot be mutated or deleted.
2. **Append-Only Event Log**: The `run_events` table is append-only. No records in this table should ever be `UPDATE`d or `DELETE`d.

## Foreign Keys & Cascades
1. **Strict Cascade Policies**: Cascade deletes should only be used where the child object's lifecycle is strictly bounded by the parent's lifecycle (e.g., deleting a Run deletes its Tasks and Events).
2. **Loose References**: High-level cross-domain links (e.g., Evaluation Results linking back to Model Outputs) should carefully consider `SET NULL` versus `CASCADE` depending on reporting needs.

## Enums
1. **Enum Governance**: Enums must be defined via `ENUM` types in PostgreSQL. Do not remove enum values in migrations, as it requires complex and dangerous table rewrites. Instead, deprecate them in application logic.
