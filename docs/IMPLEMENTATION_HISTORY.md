# Implementation History

This document tracks all major implementation milestones for Atlas.

## Milestone: Atlas CLI v2 — Execution Authority (Slice 1) & Published Discovery / Real Submit Authz (Slice 2)
- **Date**: August 2026
- **Branch**: `feature/atlas-cli-v2`
- **Purpose**: Make the Atlas CLI agent-operable with truthful execution reads and a browsable, authorizable catalog → submit chain.
- **Files changed**: `apps/backend/routers/executions.py`, `apps/backend/routers/benchmarks.py`, `apps/backend/authz.py` (slice 1), tests (`tests/backend/test_execution_authority.py`, `tests/backend/test_published_benchmark_discovery.py`, `tests/_fakes.py`, `tests/backend/conftest.py`, contract/authz suites).
- **Reason**: `GET /executions/{id}` reported engine-internal state that drifted from the authoritative `executions` row; catalog reads of published benchmarks 403'd for non-member users while submissions passed a no-op permission stub — a discovery gap and an authorization hole.
- **Impact**: `run get` now reads the authoritative row (status/timestamps/progress consistent with reports/dashboard). Published benchmarks and their versions are readable by any authenticated user; `run submit` is authorized for published benchmarks or drafts of an organization the caller is an active member of; `dispatch-targets` exposes only published + own-org drafts.
- **Current status**: Complete. Backend, CLI (322), SDK (165) suites green; live backend verified.

### Slice 4: safe `run submit` (required `--target-model`) + cost-free `--preview`
- **Date**: August 2026
- **Purpose**: eliminate the silent paying default on submissions and add a deterministic, read-only dry-run so agents can preflight before POSTing.
- **Files changed**: `cli/cli/commands/run.py` (`--target-model` now required; new `--preview` flag; `_render_submit_preview` + `_adapter_kind`), `cli/tests/test_run.py` (13 new tests + legacy submit call sites migrated), SDK (`atlas_sdk/client.py` `list_dispatch_targets()`, `atlas_sdk/models/executions.py` `DispatchTarget`, `sdk/tests/test_client.py` contract tests), `docs/guides/atlas-cli-v2-implementation-plan.md`, `docs/guides/atlas-cli-manual-testing.md`.
- **Reason**: `run submit` defaulted to `gemini-2.5-flash` — a paid real-provider model an agent could submit "innocently". v2 requires an explicit model and offers a no-POST plan.
- **Impact**: `submit` without `--target-model` is a usage error (exit 2). `--preview` resolves the version against the backend's `dispatch-targets` (published + own-org drafts, with the backend's own default dataset resolution) via a single read-only GET and prints `benchmark_name`/`version_string`/`dataset_version_id`/`target_model`/`adapter_kind` (advisory `mock|mocked` → mock, else real). Zero POSTs. Non-dispatchable version → exit 5. Real submit path byte-identical apart from the required option.
- **Current status**: Complete. CLI suite 348 passed, SDK 169 passed/2 skipped, ruff + mypy clean on touched files; live-verified (published `55555555-…` preview in JSON/human/quiet + real adapter, unknown/draft → exit 5, missing `--target-model` → exit 2, real submit → exit 0 QUEUED).

### Slice 3: `atlas run watch --timeout` (wall-clock bound, exit 9)
- **Date**: August 2026
- **Purpose**: deterministic cap on `watch` so agents can bound total wait time and re-poll.
- **Files changed**: `cli/cli/commands/run.py` (wall-clock deadline + capped sleep + `_exit_watch_timeout`), `cli/cli/errors.py` (`EXITCODE_WATCH_TIMEOUT = 9`), `cli/tests/test_run.py` / `test_exit_codes.py` / `test_cli_parsing.py` (13 new tests, incl. one real-wall-clock test), exit-code table + stale slice-1/2 sections in `docs/guides/atlas-cli-manual-testing.md`.
- **Reason**: `watch` polled indefinitely on a stuck run; only Ctrl-C (130) or the 3-failure network cap stopped it, giving agents no way to bound wait time.
- **Impact**: `--timeout N` (float, omitted = unbounded; explicit `0`/negative rejected) caps the poll loop by wall clock without oversleeping; on expiry exit 9 with the last non-terminal state (JSON) / clear message (human) / silence (quiet). Polling behavior, interval default, and the 3-consecutive-network-failure cap are untouched.
- **Current status**: Complete. CLI suite 335 passed; live-verified against a real QUEUED execution (`05282d72-…` → exit 9 each mode), a completed run within bound (exit 0), and `--timeout 0`/`-5` (exit 2).

## Milestone: Project Initialization
- **Date**: Pre-2026
- **Branch**: `main`
- **Purpose**: Scaffold the base evaluation platform architecture.
- **Files changed**: Extensive scaffolding of `apps`, `packages`, `services`.
- **Reason**: To create an extensible, domain-driven LLM evaluation engine.
- **Impact**: Established the foundational patterns (Repository, Celery workers).
- **Current status**: Stable and complete.

## Milestone: Dockerization & Architectural Audit
- **Date**: July 2026
- **Branch**: `feature/dockerization`
- **Purpose**: Audit the architecture and rollout a comprehensive, production-ready Docker infrastructure.
- **Files changed**: `.dockerignore`, `docker-compose.yml`, `docker-compose.prod.yml`, `docker/backend/Dockerfile`, `docker/frontend/Dockerfile`, `alembic/env.py`, `.env.example`.
- **Reason**: The project required a repeatable, isolated runtime environment decoupled from host dependencies.
- **Impact**: Enabled single-command startup (`docker compose up`) and identified/fixed a critical migration bug regarding SQLite fallback.
- **Current status**: Implemented, pending a final runtime validation on a Docker-equipped host.

### Fix: Alembic Dependency Graph Collision
- **Date**: July 2026
- **Reason rewritten**: A catastrophic schema dependency collision in the migration graph prevented the application from starting in Postgres.
- **Root Cause**: Two parallel branches (Execution Refactor and Execution Service) created contradictory schemas. Branch B2 dropped `atlas_runs` while Branch B1 created tables referencing it. Alembic autogenerated the table drop but omitted the `DROP CONSTRAINT` statements for the incoming foreign keys. 
- **Why fix-forward was impossible**: A new migration cannot execute because the pipeline crashes on the broken historical migration, aborting the transaction before reaching any forward fix.
- **Why rewriting history was safe**: These migrations were never deployed to any shared production or long-lived staging database. They were purely localized development artifacts.
