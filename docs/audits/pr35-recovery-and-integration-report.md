# Atlas PR #35 — Recovery & Integration Report

**Prepared for:** PR #35 author
**Purpose:** Document what was found in the original PR, what was recovered, what was already superseded, what remains useful, and what issues were discovered during local integration testing.
**Prepared from:** PR #35 diff, `docs/audits/pr35-recovery-audit.md`, current production `main`, PR #44 (`feature/recover-pr35-integration`), and results of running PR #44 locally.
**Date:** 2026-08-19

---

## 1. Executive Summary

PR #35 (`feat: integrate PR28 agent and billing capabilities`) contained substantial, useful work. It was developed against an **older Atlas architecture** and could not safely be merged directly into the current production v1 — the branch is 108 commits behind `main`, conflicts, and predates the Vercel/Supabase/Render deployment, RLS, the outbox event pipeline, worker wake, and the current frontend architecture.

> This is not a rejection of the work. The goal was to preserve the valuable functionality while protecting the current production baseline.

The good news: **most of the PR's substance is already part of current Atlas v1.** The agent backend, the entire billing stack, authentication changes, execution DTOs, and the LLM registry were integrated into `main` as Atlas evolved (several files are byte-identical between PR #35 and `main`). What was *not* yet present — the frontend↔backend **real-data integration** — was recovered selectively into **PR #44**, which also surfaced and fixed two pre-existing backend bugs. The remaining frontend agent UI is deferred to a future **Atlas Agent v2**.

Current status: production baseline protected; PR #35 remains open and unmerged; PR #44 remains open and unmerged; no production deployment was changed by this report.

---

## 2. Original PR #35 Scope

| Attribute | Value |
|---|---|
| PR | https://github.com/Synthesis-works/atlas/pull/35 |
| Branch | `integration/pr28-agent-billing` |
| Head commit | `5cb8ebc` (1 squashed commit) |
| Base at branch time | `0c410c3` |
| Merge-base with `main` | `0c410c3` |
| Staleness | 108 commits behind `main` |
| Size | 157 files, +13,662 / −795 |
| Mergeability | CONFLICTING (never merges cleanly) |
| State | OPEN, no comments |

Inventory of the contribution:

```text
Agent
 ├── agent loop, planner, memory, state
 ├── providers (gemini, grok, groq, mistral, mock) + router + schema utils
 ├── tools (benchmark, dataset, evaluation, execution, clarification, memory, registry)
 ├── approval / clarification
 ├── backend router + lifespan + config wiring
 ├── tests (core, provider contracts, failover, report integrity/export)
 └── frontend (services, polling, status, types, dashboard/layout/report/run pages,
     approval & clarification cards, sidebar, timeline)

Billing
 ├── models (credit accounts, invoices, payments, prices, products, refunds,
     subscriptions, usage records, webhook events)
 ├── repositories
 ├── gateways (stripe, razorpay) + registry
 ├── services (billing/service.py)
 ├── API router + schemas
 └── migration bee5b46e2c75

Frontend integration
 ├── benchmark API (api/mapper/hooks)
 ├── dataset API
 ├── model registry (useModelCatalog, provider grid)
 ├── authentication (authApi, authStore, ProtectedRoute)
 ├── experiment / evaluation / execution API services + polling
 ├── projects API + store
 └── infrastructure/api/client.ts (axios) + react-query provider
```

---

## 3. What PR #35 Contributed

- **Agent engine**: a complete planning/execution loop with provider failover, memory, tool registry, approval and clarification flows, report generation/export, and an extensive backend test suite (provider contracts, failover, report integrity).
- **Billing**: a full subscription/billing domain (models, repositories, stripe + razorpay gateways, service layer, API routes, schemas, migration).
- **Frontend integration**: real API services for benchmarks, datasets, experiments, evaluations, executions, projects, models, and auth — replacing mock/hard-coded data with backend calls; plus an agent UI (dashboard, workspace run view, report page, timeline, approval/clarification cards).
- **Auth**: login via email *or* username identifier (`UserLogin.login_identifier`).
- **Execution**: `total_items` / `completed_items` / `target_model` on execution DTOs.
- **LLM registry**: `packages/llm/registry.py` (providers/models/availability).
- **Migration**: `organization_members` auditable columns (`0d95e9384c25`).

---

## 4. What Was Already Preserved in Current Atlas v1

Credit where it is due — the following from PR #35 is **already live on `main`** (verified by byte-level comparison):

| PR #35 area | Status on `main` | Evidence |
|---|---|---|
| Agent backend (loop, planner, memory, providers, tools, router, state, tests) | 🟢 Present | Same file set; `apps/backend/agent/**` exists; agent router mounted under `/api/v1/agent/*`; main intentionally disables Grok (deprecated models) — the PR's Grok file is the pre-disable version |
| Billing (models, repos, gateways, service, router, schemas) | 🟢 Present | `routers/billing.py`, `services/billing/service.py`, `models/billing.py` are **byte-identical** between PR #35 head and `main`; `/api/v1/billing/*` routes live; stripe/razorpay deps in the lockfile |
| Auth identifier login | 🟢 Present | `schemas/auth.py` + `services/auth.py` on `main` |
| Execution DTOs (`total_items`, `completed_items`, `target_model`) | 🟢 Present | `packages/execution_engine` on `main`; returned by the live API |
| LLM registry (`packages/llm/registry.py`) | 🟢 Present | **Byte-identical**; exposed via the API |
| `organization_members` auditable columns | 🟢 Present | Folded into `main`'s rewritten baseline migration `7537275102f0` (never re-apply the old migration) |

No recovery work was needed for these; they were integrated as Atlas moved past the PR's base commit.

---

## 5. What Was Recovered Selectively into PR #44

PR #44 (`feature/recover-pr35-integration`) extracted the recoverable frontend↔backend integration intent that was **not** yet on `main`:

- **Real benchmark catalog integration** — `useBenchmarkCatalog` now calls `GET /api/v1/benchmarks` (real data: 8 benchmarks verified locally) instead of `MOCK_BENCHMARKS`.
- **Real dataset catalog integration** — new `projectService` (organizations → projects resolution with localStorage cache) + `datasetService` hitting the correct project-scoped endpoint `GET /api/v1/projects/{project_id}/datasets` (the old call targeted a non-existent `/api/v1/datasets`).
- **Real model registry integration** — new `modelService` for `GET /api/v1/models` with DTO→`RegistryModel` mapping; `useModelCatalog` **and** the page-wide `modelsStore` (fleet hero, drawer, compare, command palette) now use registry data instead of 50 fabricated models.
- **Project resolution** — org → project lookup chain with caching.
- **Removal of fake evaluation mock data** — `domain/evaluations/mock.ts` deleted (provably unreferenced).
- **Removal of fake catalog fallbacks** — `benchmarkService` no longer silently returns `MOCK_BENCHMARKS` on error; empty/error responses are honest.
- **`/api/v1/models` backend fix** — `AdapterFactory.get_available_models()` delegating to the LLM registry (the endpoint's implementation previously did not exist).
- **Honest loading/error/retry behavior** — all three catalogs fetch on mount with real loading, error, and retry states.

**Follow-up fixes added during local testing (same branch, commit `c68e10b`):** mounting the previously-dead `models.router` in `main.py` (fixed 404 on `/api/v1/models`), and repairing `DatasetService.list_datasets` (`.session` → `.db`; fixed 500 on the datasets endpoint). Both verified live locally; ruff/mypy clean; backend tests 13 passed; CI green on PR #44.

---

## 6. What Was Intentionally Deferred

| Area | Why | Planned home |
|---|---|---|
| Agent frontend UI (AgentDashboard, AgentLayout, AgentReportPage, AgentWorkspaceRun, approval/clarification cards, sidebar, timeline) | Genuinely valuable and still missing on `main`, but the agent backend/API contract has evolved since the PR; importing the old UI wholesale would conflict with the current workspace architecture | Future **Atlas Agent v2** PR against the current Agent API |
| `ProjectExecutionListEntry` DTO (benchmark_name, duration in execution lists) | Nice-to-have; current list endpoint works | Small follow-up if desired |

---

## 7. What Was Considered Obsolete or Conflicting

| PR #35 piece | Why rejected |
|---|---|
| `infrastructure/api/client.ts` (axios) + react-query provider | Superseded by `core/api/client.ts` (fetch, envelope unwrap, single-flight re-auth) |
| Frontend pages restructure (`pages/workspace/*`, `features/projects`) | Superseded by the newer structure (`features/dashboard`, `leaderboard`, `reporting`) |
| `uv.lock` / `pyproject.toml` / test-suite edits | Branch-era dependency state; `main`'s lockfile is authoritative |
| Grok-enabled agent provider config | Predates the intentional Grok disable on `main` (deprecated models, no credits) |
| Old migrations (`0d95e9384c25`, `bee5b46e2c75`) | Superseded by the rewritten baseline `7537275102f0` (columns/tables already present) |

---

## 8. Local Integration Testing

**Methodology** (nothing deployed; production untouched):
- Checked out the exact PR #44 branch (`feature/recover-pr35-integration` @ `5c356f0c`, later `c68e10b`); HEAD verified equal to PR head.
- Used the repository's documented one-click dev procedure (`start_atlas.cmd` equivalents): backend uvicorn :8000, outbox sweep loop, frontend vite :5173.
- **Database target: local SQLite `atlas_dev.db`** — the documented launcher overrides `.env`'s Supabase production `DATABASE_URL`; every write verified to land in the local file only. No production connection was made.
- All real provider keys exist in local `.env` (Gemini, Groq, Mistral, NVIDIA, xAI), so real executions were possible.

**Test status matrix:**

```text
CI tests              ✅   (test job + 3 Vercel previews pass on PR #44)
Local API testing     ✅   (health, openapi, auth, benchmarks, projects, datasets,
                            models, executions, dashboard, agent, reports)
Manual UI testing     ⚠️   (browser opened locally; real UI-triggered executions ran
                            end-to-end; visual catalog checks partially verified)
Production testing    ❌   (not intentionally deployed; production never touched)
```

**Key results:**
- `GET /health` 200; `/openapi.json` 72 routes; login (demo creds) 200.
- Benchmarks: 8 real records served to the catalog.
- Real execution: `groq/openai/gpt-oss-20b` on MBPP → **COMPLETED** in ~6s with 2 real persisted model outputs (2.7s / ~2,150 tokens each — actual LLM content, not mock).
- Agent run via the local UI: `gemini-3.5-flash-lite` execution **COMPLETED** with real outputs; `grok-2-latest` failed honestly (provider 404 — stale registry name, see §10).
- A UI-submitted benchmark execution (`AI Coding Testing and Safety Benchmark`, gpt-oss-20b) **COMPLETED** — proving the browser → backend → provider chain.

---

## 9. Manual UI/UX Findings

Issues discovered while running PR #44 locally. Markers: **[code]** = confirmed by code reading, **[API]** = confirmed via live API test, **[manual]** = observed during manual/browser testing, **[unverified]** = suspected.

| Area | Problem | Severity | Evidence | Appears in | Likely cause | Suggested direction |
|---|---|---|---|---|---|---|
| Model catalog | `/api/v1/models` returned 404 → catalog showed error state (now fixed: router was never mounted) | High | [API] | main & PR #44 (pre-fix) | `models.router` defined but not included in `main.py` | ✅ fixed in PR #44 (`c68e10b`); re-verify in browser |
| Dataset page | Datasets endpoint returned 500 → catalog error state (now fixed) | High | [API] | main & PR #44 (pre-fix) | `DatasetService.list_datasets` used `.session`; repository exposes `.db` | ✅ fixed in PR #44 (`c68e10b`); re-verify in browser |
| Benchmark catalog | Real data loads correctly; when the API fails the UI now shows an honest error/empty state instead of mock data (intentional behavior change) | Low | [API] | PR #44 | — | Confirm the empty state copy is user-friendly |
| Model selector | Registry marks `groq/llama-3.3-70b-versatile` and `grok-2-latest` as `available=True`, but the providers 404 those model names → user selects a "ready" model and the run fails | High | [API] | main & PR #44 | Stale model names in `packages/llm/registry.py` | Clean up registry names to real provider IDs (e.g. `gpt-oss-20b`) |
| Models page widgets | `modelsStore` silently ignores fetch failures (only sets data on success; no error surface) | Medium | [code] | main & PR #44 | Store fetch effect has no error state | Add store-level error/retry, or share the catalog's error state |
| Execution detail | COMPLETED runs show `completed_items 0/N` and empty `started_at/completed_at` in the API/UI | Medium | [API] | main & PR #44 | Execution DTO mapping quirk (pre-existing) | Fix DTO hydration of progress timestamps |
| Leaderboard/evaluations (local dev only) | After a local run, eval results and leaderboard snapshot never appear | Medium | [API] | main & PR #44 (dev-only) | Local outbox sweep requires Redis (absent in one-click dev) + dispatcher exception-handler bug (§10) | Prod pipeline verified working; add Redis to local dev or fix the dispatcher error path |
| Agent UI | Not present in PR #44 at all (deferred to Agent v2) | High | [code] | main | — | Separate Agent v2 effort against current Agent API |
| Loading states | Catalogs show loading until fetch resolves; models page widgets have no loading indicator | Medium | [code] | PR #44 | Store has no loading flag | Add `isLoading` to modelsStore context |

Screenshots: none captured during this run; the local browser session is still open at http://localhost:5173 for direct inspection.

---

## 10. Backend/API Findings

All pre-existing on `main` unless noted; none were introduced by PR #44 (PR #44 merely stopped masking them with mock data).

| # | Finding | Status | Fix |
|---|---|---|---|
| 1 | `GET /api/v1/models` 404 — models router never mounted | ✅ fixed in PR #44 | Mount `models.router` under `/api/v1` in `main.py` (covers prod via the Vercel shim) |
| 2 | `GET /projects/{id}/datasets` 500 — `DatasetService` used `repo.session` (attribute is `.db`) | ✅ fixed in PR #44 | One-line change `services/datasets.py:31` |
| 3 | `GET /api/v1/search` 500 — `Benchmark.description` does not exist on the model | ⚠️ open | `services/search/providers/benchmark.py:30` — drop/replace the attribute reference |
| 4 | Outbox dispatcher exception handler crashes — `logger.error("...", event=...)` collides with structlog's `event` kwarg → messages stay PENDING/FAILED | ⚠️ open (dev impact only; prod pipeline verified working) | `outbox_dispatcher.py:126` — rename the kwarg |
| 5 | Local outbox sweep needs Redis; one-click dev has none | ⚠️ open (dev only) | Document or add Redis to dev setup |
| 6 | Stale registry model names (`llama-3.3-70b-versatile`, `grok-2-latest`) | ⚠️ open | Registry cleanup to real provider model IDs |
| 7 | `completed_items`/`started_at` not hydrated on COMPLETED runs | ⚠️ open (cosmetic) | Execution DTO mapping fix |

---

## 11. Architecture / Compatibility Issues

Why the historical branch could not be merged wholesale:

```text
PR #35 architecture                 Current Atlas v1
        ↓                                  ↓
old Atlas (pre-deployment)         Vercel (web + API)
                                    Supabase (Postgres + RLS)
                                    Render (worker + outbox sweep)
                                    outbox event pipeline + worker wake
                                    new frontend architecture (core/api client,
                                    workspace interaction store, feature folders)
```

Concretely: RLS-protected Supabase schema vs. the PR's pre-RLS assumptions; outbox-driven execution/event flow vs. direct dispatch; the current API client (fetch, envelope unwrap, single-flight re-auth) vs. the PR's axios client; and the current workspace frontend structure vs. the PR's page restructure. These make direct merging impossible without substantial modernization — which is what PR #44 does for the parts that matter.

---

## 12. Current Status of PR #35

- **OPEN**, unmerged, `mergeable: CONFLICTING`, 108 commits behind `main`, no comments.
- No changes to PR #35 were made during this effort; it remains as its author left it.
- It is not expected to be merged as-is; its value is being carried forward via `main` (already-integrated areas), PR #44 (recovered integration), and future Atlas Agent v2 work (agent frontend).

---

## 13. Recommended Next Steps

1. Review PR #44 (catalogs on real data + the two backend fixes). It is ready for merge after final browser confirmation of the three catalogs.
2. Fix the small pre-existing backend items in follow-ups: search provider (`#3`), outbox dispatcher error path (`#4`), registry model names (`#6`), execution DTO progress fields (`#7`).
3. Plan **Atlas Agent v2**: bring the agent frontend from PR #35 forward against the current Agent API, reusing the agent services/types already on `main`.
4. Keep PR #35 open as historical reference, or close it with a link to this report and PR #44 so the record is traceable.

---

## 14. Potential Collaboration

The original PR contains valuable work. Rather than merging the historical branch wholesale, this report is the basis for selectively modernizing the remaining pieces against current Atlas v1. Concrete areas where the original author's help would be welcome:

```text
Agent frontend  → modernize against the current Agent API (Agent v2)
Billing frontend → adapt/verify the billing UI against the live /api/v1/billing/* API
UI integration  → fix remaining catalog/detail interactions found in §9
Model registry  → align registry entries with real provider model IDs
```

---

## Contribution Matrix

| Original PR #35 area | Current status | Action |
|---|---|---|
| Agent backend (loop, planner, memory, providers, tools, router, tests) | already on main | preserved — none |
| Billing (models, repos, gateways, services, API, schemas) | already on main (byte-identical files) | preserved — none |
| Auth identifier login | already on main | preserved — none |
| Execution DTOs (`total_items`/`completed_items`/`target_model`) | already on main | preserved — none |
| LLM registry | already on main | preserved — none |
| `organization_members` auditable columns | folded into rewritten baseline | preserved — none |
| Frontend↔backend real-data integration (benchmarks, datasets, models, project resolution, honest states) | recovered into PR #44 | review PR #44 |
| `/api/v1/models` endpoint implementation + mounting | recovered into PR #44 | review PR #44 |
| Agent frontend UI (dashboard, run page, report, timeline, approval/clarification) | deferred | future Atlas Agent v2 |
| `ProjectExecutionListEntry` DTO | deferred (low value) | optional follow-up |
| axios client + react-query provider | obsolete | none |
| Frontend page restructure | obsolete (superseded) | none |
| `uv.lock`/`pyproject`/test-suite edits | obsolete | none |
| Stale registry model names | still broken | follow-up fix |
| Search endpoint (`Benchmark.description`) | still broken | follow-up fix |
| Outbox dispatcher error path + Redis-free local sweep | still broken (dev only) | follow-up fix |

---

## Status Guarantees

- ✅ Current production baseline remains protected.
- ✅ PR #35 remains unmerged (OPEN).
- ✅ PR #44 remains unmerged (OPEN).
- ✅ No production deployment (Vercel, Render, Supabase) was changed by this report or the local testing it documents.