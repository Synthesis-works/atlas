# PR #35 Recovery Audit — `integration/pr28-agent-billing` vs production `main`

**Date**: 2026-08-19
**PR**: https://github.com/Synthesis-works/atlas/pull/35 (OPEN, `mergeable: CONFLICTING`)
**Head**: `5cb8ebc` (1 squashed commit) · **Base at branch time**: `0c410c3` · **Merge-base**: `0c410c3`
**Staleness**: 108 commits behind `main` · own diff: 157 files, +13,662/−795
**Decision**: DO NOT MERGE. Recover valuable intent selectively. (Verdict confirmed: branch predates Vercel/Supabase/Render deployment, RLS, outbox worker, login warm-up, v1 snapshot.)

## Classification legend

- **A** — still valuable / not on main
- **B** — already implemented on current main
- **C** — obsolete / superseded
- **D** — conflicting / dangerous
- **E** — unknown, needs manual review

## Area-by-area classification

| Area | Class | Evidence |
|---|---|---|
| Agent backend (tools, providers, planner, executor, router, state, tests) | **B** | File set is identical to `main` (`apps/backend/agent/**`); main intentionally disabled Grok (deprecated models, no credits) — PR #35's Grok file is the pre-disable version |
| Agent API router (`/api/v1/agent/*`) | **B** | `routers/agent.py` exists on main with same task/permission contract |
| Auth (UserLogin email/username/identifier, `login_identifier`, login-by-identifier) | **B** | `schemas/auth.py` + `services/auth.py` on main contain the same changes |
| Execution engine (`total_items`, `completed_items`, `target_model`, DTOs) | **B** | `packages/execution_engine/domain/models.py` + `api/dtos.py` on main; production API returns these fields |
| LLM registry & prompt defaults | **B** | `packages/llm/registry.py` (same model entries), `Prompt.system` default |
| `organization_members` auditable columns migration (`0d95e9384c25`) | **B/C** | Folded into main's rewritten baseline migration `7537275102f0` (columns present) — never re-apply |
| Billing (models, migration `bee5b46e2c75`, services, router, schemas, frontend) | **— (excluded)** | Phase 4: separate future feature; no billing tables on main |
| `infrastructure/api/client.ts` (axios) + react-query provider | **C** | Superseded by main's `core/api/client.ts` (fetch, envelope unwrap, single-flight re-auth) |
| Frontend page restructure (`pages/workspace/*`, `features/projects`) | **C** | Superseded by main's newer structure (`features/dashboard`, `leaderboard`, `reporting`, `pages/workspace` with its own components) |
| `uv.lock` / `pyproject.toml` / test-suite edits | **C** | Branch-era deps; main's lockfile is authoritative |
| Agent frontend UI (`pages/workspace/agent/*`, AgentDashboard/AgentLayout/AgentReportPage/AgentWorkspaceRun, approval/clarification/sidebar/timeline) | **A** | Genuinely missing on main (main has only agent services + types/status). Phase 3 verdict: future **Atlas Agent v2** work — do not import into this change |
| `ProjectExecutionListEntry` DTO (benchmark_name, duration in execution list) | **E (low)** | Nice-to-have; main's list endpoint works — defer |
| Frontend ↔ backend real-data integration intent | **A** | The core recoverable intent — see gap analysis |

## Phase 2 — frontend/backend integration gap analysis (current `main`)

Backend APIs are present and live. Frontend **services exist** (`core/api/client.ts` + per-feature services) but **three catalog data sources bypass them and render mock data**:

| Surface | Current source (mock) | Real API available | Gap |
|---|---|---|---|
| Benchmark catalog (`useBenchmarkCatalog`) | `MOCK_BENCHMARKS` + fake 1200 ms delay | `GET /api/v1/benchmarks` (auth'd, paginated, `BenchmarkRead`) | Hook never calls `getBenchmarks()` |
| Dataset catalog (`useDatasetCatalog`) | `mockDatasets` + random `mockHealthMap`/`mockQualityMap` scores | `GET /api/v1/projects/{project_id}/datasets` (auth'd, project-scoped) | Hook uses mocks; `datasetService.getDatasets()` calls the non-existent `/api/v1/datasets` (broken-dead) |
| Model catalog (`useModelCatalog`) + `modelsStore` | `MOCK_MODELS` (50 fabricated models) + fake delay | `GET /api/v1/models` | Endpoint is **broken** (`AdapterFactory` lacks `get_available_models` → 500 error envelope); no frontend service exists |
| `benchmarkService` fallbacks | `getBenchmarks()`/`getBenchmarkById()` silently return `MOCK_BENCHMARKS` on error | — | Silent fake data on failure |

Remaining mock surfaces intentionally left alone (documented, not part of this recovery): public marketing `pages/Benchmarks.tsx` (no auth → mock showcase), `DatasetsPage` hero/analytics/storage embellishment panels, governance components (unrendered), `workspaceStore` initial state.

## Phase 3 — Agent verdict

PR #35's agent backend is already on main. Its agent **frontend** is valuable but belongs in a separate **Atlas Agent v2** PR (main's agent API + services are ready for it). Not integrated in this change.

## Phase 4 — Billing

Excluded entirely. No billing code, migration, or schema is brought over.

## Phase 5 — Recovered functionality (this change)

1. Benchmark catalog → real `GET /api/v1/benchmarks` (remove mock fallback from service).
2. Dataset catalog → real project-scoped datasets endpoint, with org→project resolution.
3. Model catalog + models store → real `GET /api/v1/models`; backend fix: `AdapterFactory.get_available_models()` delegating to `packages/llm` registry.
4. Honest loading/error/retry states; delete dead mock modules where provably unreferenced.