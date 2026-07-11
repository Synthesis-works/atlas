# Database Readiness Review: Atlas V1 Schema

Assuming the schema is frozen, the following are significant architectural issues that will likely necessitate complex and painful schema migrations once the Execution and Evaluation services are built out and scaled.

## 1. Index Strategy Regrets
**Issue:** Missing indexes on highly queried filtering columns.
* `AtlasRun.status`: The execution engine will constantly poll for `status = 'PENDING'` runs. Without an index, this will result in full table scans on what will become the largest table in the database.
* `AtlasRun.target_model`: Researchers will frequently filter runs by model (e.g., all "gpt-4" runs). This column needs an index.
* `Benchmark.status` and `Benchmark.name`: Missing indexes for dashboard filtering and searching.

## 2. Unique Constraint Regrets
**Issue:** Missing composite unique constraints for versioned entities.
* Currently, multiple rows in `BenchmarkVersion`, `DatasetVersion`, `ExecutionAdapterVersion`, and `EvaluationStrategyVersion` can share the exact same `version_string` (e.g., "v1.0") for the exact same parent entity (`benchmark_id`). 
* Without composite unique constraints (e.g., `UniqueConstraint('benchmark_id', 'version_string')`), race conditions during concurrent authoring or execution will result in duplicate version strings, breaking the deterministic nature of the benchmark runs.

## 3. Delete Behavior (Cascade vs Restrict)
**Issue:** Missing `ondelete="CASCADE"` on closely coupled child entities.
* Child entities like `BenchmarkVersion` do not have `ondelete="CASCADE"` on their foreign key to `Benchmark`. 
* Same for `ModelOutput` and `Artifact` referencing `AtlasRun`.
* While soft deletes mitigate some of this, if a user legitimately requests a hard delete (e.g., for GDPR compliance or to wipe a corrupted run), the database will reject the deletion via a `RESTRICT` violation (SQLAlchemy's default behavior). The application would be forced to manually delete millions of `ModelOutput` rows one-by-one before deleting the `AtlasRun`, causing massive application-level memory bloat and timeouts.

## 4. Enum Evolution Regrets
**Issue:** Using native PostgreSQL ENUMs for highly volatile state machines.
* `RunStatus` and `BenchmarkState` are implemented as native Postgres `ENUM` types. 
* Alembic does not natively support autogenerating migrations for adding or removing Enum values. Adding a new state (e.g., `TIMEOUT` or `RATE_LIMITED` to `RunStatus`) requires developers to write custom `op.execute("ALTER TYPE run_status ADD VALUE 'TIMEOUT'")` migrations. Removing or renaming an enum value in Postgres requires a massive table rewrite.
* For state machines that evolve rapidly, using a `String` column coupled with an application-level enum (or a standard `CheckConstraint`) is far more scalable and prevents migration headaches.

## 5. JSONB Usage Regrets
**Issue:** `EvaluationResult` has five separate JSONB columns (`raw_measurements`, `judge_outputs`, `warnings`, `failure_reasons`, `evaluation_logs`).
* While JSONB is great for unstructured metadata, packing execution logs and judge outputs directly into the `evaluation_results` table row will cause massive row bloat. PostgreSQL TOASTs large JSONB payloads, but having 5 per row will severely degrade the performance of sequential scans on `evaluation_results` (e.g., when calculating aggregate win rates).
* **Recommendation:** Large, read-rarely outputs like `evaluation_logs` and `judge_outputs` should either be stored as `Artifact` records (in object storage) or moved to an isolated `evaluation_result_details` table to keep the main `evaluation_results` table lean for fast analytical queries.
