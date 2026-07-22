# Database Strategy

This document outlines the architectural decisions, supported technologies, and operational policies regarding the database layer in the Atlas Benchmarking Platform.

## 1. Supported Database: PostgreSQL

Atlas is fundamentally designed as a **PostgreSQL-first** application. 

### Why PostgreSQL was chosen
The platform's execution and evaluation engines have complex consistency, concurrency, and schema requirements. We intentionally rely on native PostgreSQL features to satisfy these requirements robustly and elegantly, avoiding application-layer workarounds.

### Required PostgreSQL Features
- **`JSONB`**: Used extensively in `ExecutionWorker.capabilities`, `RunEvent.metadata`, and `CapabilityProfile.score_explanation` for high-performance schema-less querying.
- **`UUID`**: Native UUID columns are used for all primary keys (Aggregate IDs) across the distributed system to prevent ID collisions and simplify disconnected generation.
- **`FOR UPDATE SKIP LOCKED`**: Essential for the `OutboxDispatcher` to allow multiple concurrent sweepers to acquire pending outbox messages without blocking or deadlocking each other.
- **`ENUM` Evolution**: We utilize PostgreSQL native Enum types (e.g., `run_status`, `task_status`, `event_type`) and `ALTER TYPE` to enforce domain-level invariants at the schema level.
- **Transactional DDL**: Crucial for ensuring that schema migrations either succeed entirely or roll back safely without leaving the database corrupted.

### Unsupported for Runtime Verification: SQLite
While SQLite is supported for isolated, in-memory unit testing of standard CRUD repositories, **SQLite is NOT supported for runtime verification or production**. The lack of native Enum alteration, `SKIP LOCKED` row-level concurrency, and transactional schema modifications (`ALTER TABLE DROP CONSTRAINT`) makes it incompatible with the Atlas architecture.

---

## 2. Migration Policy (Alembic)

To maintain a stable, predictable, and team-friendly database history, the following rules apply to all Alembic migrations:

1. **Never Edit Released Migrations**: Once a migration has been committed and merged into the main branch (i.e., released or shared with others), it is **frozen**. It must never be modified.
2. **Use Corrective Migrations**: If an error is discovered in a previous migration (e.g., a missing column, incorrect constraint, or a syntax error on a specific dialect), do **not** fix the old file. Create a new "corrective" migration (`uv run alembic revision -m "fix X in Y"`) to apply the change.
3. **Merge Heads Intentionally**: If parallel branches create multiple migration heads, do not artificially rewrite `down_revision` to force a linear history. Instead, use a merge migration (`uv run alembic merge heads`) to explicitly record the convergence.

---

## 3. Local Development Setup

For local development and verification, a PostgreSQL instance is strictly required. 

### Docker Compose
Developers should spin up the required infrastructure using the provided `docker-compose.yml`:

```bash
docker-compose up -d postgres
```

Ensure your `.env` file points to the local container:

```env
DATABASE_URL=postgresql://atlas_user:atlas_pass@localhost:5432/atlas
```

### Backup and Restore Strategy
* **Automated Backups**: Production databases are backed up continuously using WAL archiving (e.g., via pgBackRest or similar tools) to support point-in-time recovery (PITR).
* **Logical Backups**: Nightly `pg_dump` snapshots are taken for disaster recovery and offline analysis.
* **Restore Testing**: Database restoration procedures must be tested quarterly in a staging environment to ensure data integrity.
