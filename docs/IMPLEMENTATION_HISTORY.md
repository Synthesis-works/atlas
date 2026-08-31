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

### Slice 5: expose SDK retry capability via global `--retries`
- **Date**: August 2026
- **Purpose**: surface the SDK's existing `max_retries` (default 3) through the CLI so agents can tune retry resilience, without re-inventing retry.
- **Files changed**: new `cli/cli/client.py` (`build_client(cfg, *, token_supplier=None, timeout=None)` — the single shared client-construction path, passing `max_retries=cfg.retries`), `cli/cli/config.py` (`AtlasConfig.retries`, `_env_int`), `cli/cli/app.py` (global `--retries` with `ATLAS_RETRIES` env + negative-value callback), all 18 `AtlasClient(...)` sites across 8 command files migrated to `build_client` (watch keeps its `timeout=5.0` override), test patch targets moved from `cli.commands.<module>.AtlasClient` → `cli.client.AtlasClient`, new `cli/tests/test_client_builder.py` (10 tests incl. real-SDK behavioral proof via a scripted transport), plus additions to `test_config.py` / `test_cli_parsing.py`.
- **Reason**: retries were hard-coded inside the SDK; the CLI had no way to lower them for fast failure or raise them for flaky networks, forcing agent scripts to accept fixed latency.
- **Impact**: `--retries N` (env `ATLAS_RETRIES`) flows into the SDK's actual retry loop for idempotent GET/HEAD only; POST (`run submit`) is never retried; default 3 keeps v1 behavior byte-identical. Negative/non-integer values exit 2 (flag *and* env). Live-verified: healthy GETs round-trip at 0/3/5; against a hanging port `--retries 0` ≈ 1 attempt vs `--retries 2` ≈ 3 attempts (wire-proven by elapsed time); invalid values exit 2; authenticated `run get` and a real `run submit` POST exit 0.
- **Current status**: Complete. Commit `956763e`. CLI suite 366 passed, SDK 169 passed/2 skipped, ruff + mypy clean on touched files.

### Slice 6: offline `--json-schema` self-description (faithful-model commands)
- **Date**: August 2026
- **Purpose**: let agents discover the exact JSON shape of a command's output as a deterministic, machine-readable JSON Schema document — resolved **offline** from the SDK pydantic model, so it works exactly like `--help` (no backend round-trip).
- **Files changed**: new `cli/cli/output/schema.py` (`SchemaDocument`/`ArraySchemaDocument` + `emit_json_schema`: adds the draft-2020-12 `$schema` dialect key on top of `model_json_schema()`, whose `$defs`/`$ref` already express nested DTOs), new `cli/tests/test_json_schema.py` (31 tests), and `--json-schema` flags in `dashboard`, `run get`, `report get`, `leaderboard benchmark`, `leaderboard model` (summary + `--history` → `array[TrendPoint]` + `--benchmarks` → `array[ModelBenchmarkHistory]`), `benchmark list` (`PageResponse[BenchmarkRead]`), `benchmark get`. Docs: plan (status, slice-6 section rewritten, commit order, done-criteria), `docs/guides/atlas-cli-manual-testing.md` (command tree + new schema section + per-command examples), this file.
- **Reason**: P9/P10 from the v2 audit — agents had to guess field names; field-name drift between close-but-different endpoints was a real trap. The mandated pre-implementation review found the plan's `--fields` did NOT belong (value is covered by `jq`/`ConvertFrom-Json`; unknown-field validation would require the very schema-registry framework the mandate forbade; hand-built wrappers like `run list` — which drops `next_cursor` — make dot-path semantics drift-prone) so **`--fields` was dropped** and only `--json-schema` shipped, narrowed to commands whose JSON output is a faithful model dump.
- **Impact**: `atlas <cmd> --json-schema` prints the schema and exits 0 without constructing a client (tests assert `cli.client.AtlasClient` is never called). Nested structures (report `scores[]`, leaderboard `entries.items[]`) ride pydantic's `$defs`/`$ref`. `--quiet` still wins (silent, exit 0); `--output json` and human modes agree; excluded commands (`activity`, `run list`, `run cancel`, `report list`, `report export`, `benchmark versions`, `health`) reject the flag with a usage error (exit 2). Default output untouched.
- **Current status**: Complete. CLI suite 397 passed, SDK 169 passed/2 skipped, ruff + mypy clean. Live-verified offline (backend up, but no client is built): dashboard/run get/report get/benchmark list/leaderboard model --history schemas exit 0 with correct documents; `--quiet dashboard --json-schema` silent exit 0; `activity --json-schema` exit 2; default `--output json dashboard` unchanged.

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
