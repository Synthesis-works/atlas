# Atlas CLI Readiness Audit

- **Branch:** `audit/cli-readiness` (from `origin/main` @ `0dd49ec`, "Merge pull request #50")
- **Date:** 2026-08-23
- **Scope:** Investigation only. No CLI code was implemented. This report establishes the actual state of the repository and recommends where a future CLI should interface with Atlas.
- **Audit method:** Documentation review; end-to-end code-path tracing (frontend service → HTTP → router → application service → repository/worker → DB); local validation runs (ruff, mypy, pytest subset, frontend lint/typecheck/build). GitHub was unreachable during the audit (`git fetch` failed), so remote-state conclusions rest on the locally cached `origin/main` ref.

---

## 1. Executive Summary

Atlas is **two architectures in one repository**, and the documentation tells both stories without reconciling them:

1. **The "v1 production baseline"** (README.md): FastAPI + transactional outbox + eager Celery worker, deployed on Vercel (web + API) + Supabase Postgres + Render (worker), with a Vite+React SPA at `apps/landing`. This loop - web -> API -> DB -> outbox -> worker -> real LLM -> evaluation -> reports -> leaderboard - is documented as verified end-to-end against live production.
2. **The "Docker execution runtime"** (AGENT_HANDOFF.md, PROJECT_STATE.md, recent branches): Dockerized dev/prod compose stacks, an Executor abstraction (`LocalExecutor` / `DockerExecutor`) running benchmark attempts in hardened containers with full provenance, and - as of PR #50 merged the day before this audit - **GitHub Actions as the first production execution backend** (`EXECUTION_BACKEND=docker|github_actions|disabled`).

The backend is real, substantially tested, and coherent: ~18 routers under `/api/v1`, a layered execution engine, a transactional outbox, Alembic-managed schema (~60 tables across 12 model modules), and 127+ passing backend tests. The frontend is a polished SPA whose **core loop (auth -> benchmarks -> dispatch execution -> poll status -> reports) is genuinely integrated**, but four feature areas (Datasets catalog, Models, Providers, Experiments) are **mock-driven**, one service calls an endpoint that does not exist (Leaderboard), and one implemented router is never mounted (Models).

**CLI readiness verdict:** The cleanest CLI boundary already exists - the versioned HTTP API (`/api/v1`) backed by JWT auth. A CLI should be an HTTP client first (Option A), because the API is the only stable, tested, auth-capable contract; direct DB/domain-layer access would bypass multi-tenancy, RLS assumptions, and outbox lifecycle semantics. Several P1 issues (permission checks are decorative on global routes, no machine-client auth story beyond user JWTs, project-scoped dataset endpoints that the frontend itself ignores) should be fixed or consciously scoped around before Phase 1.

---

## 2. Repository Architecture (as implemented)

```text
apps/
  backend/            FastAPI app (main.py factory), routers, middleware,
    routers/          auth, benchmarks, datasets, executions, evaluation, reporting,
                      leaderboard, agent, billing, dashboard, organizations, projects,
                      history, search, system, internal_workers, health (+ UNMOUNTED models.py)
    services/         domain-facing service classes used by routers
    worker/           celery_app, tasks (outbox sweep + run_execution_task),
                      github_dispatcher, executor_init, stale_attempt_reaper,
                      http_entry (Render), wake_client, outbox_sweep_loop
    agent/            agentic assistant layer + its own executor.py
  landing/            Vite + React 19 + TS SPA (the real frontend; vercel.json present)
  web/                Next.js STUB - no package.json (only next-env.d.ts tracked);
                      public/ holds a standalone agent UI mounted at /agent-ui
packages/
  database/           atlas_db: 12 model modules, repositories, alembic/ (6 migrations)
  execution_engine/   api/dtos; application (ExecutionApplicationService, Executor,
                      LocalExecutor, DockerExecutor, OutboxDispatcher, scheduler);
                      domain (models/events/exceptions); persistence
  evaluation_engine/  strategies + scoring + outbox subscriber
  llm/                provider clients/registry (gemini, groq, mistral, nvidia, ollama)
  benchmark/, datasets/, auth/, core/, ...   domain libraries
services/             billing(12 files), dataset(13), evaluation-service(25),
                      execution-service(24), report(18), search(5) have code;
                      auth, auth-service, benchmark, evaluation, leaderboard,
                      notification, project, storage, user are EMPTY directories
cli/                  .gitkeep placeholders ONLY (commands/, templates/)
sdk/                  .gitkeep placeholders ONLY (python/, typescript/)
api/index.py          Vercel serverless entrypoint wrapping the FastAPI app
docker/               backend Dockerfile (multi-stage, non-root atlas user) is good;
                      frontend Dockerfile is dead commented-out Next.js config
deploy/worker/        systemd unit + Render deployment notes
tests/                backend/, benchmark/, execution/, integration/, api/, frontend/
```

Runtime topologies that actually exist in code:

| Mode | Path | Status |
| --- | --- | --- |
| LOCAL dev | `uvicorn apps.backend.main:app` + `python -m apps.backend.worker.outbox_sweep_loop` (eager Celery, no broker; SQLite fallback DB) | Documented and consistent with code |
| CLOUD v1 | Vercel serverless API + Render worker (`http_entry.py`, `/wake`, keep-alive ping) + Supabase pooler + RLS | Documented as deployed & E2E-verified (README section 14) |
| Execution backends | `EXECUTION_BACKEND`: `docker` (worker-local DockerExecutor) / `github_actions` (repository_dispatch -> runner claims PENDING attempt -> containerized run writes results to DB) / `disabled` (kill switch; executions stay QUEUED) | New as of PR #50; dry-run validated on real runners per validation report; unit-tested |

---

## 3. Documentation vs Reality

| # | Documentation says | Code reality | Verdict |
| --- | --- | --- | --- |
| D1 | README: production = Vercel + Supabase + Render, outbox-driven, Redis optional | Matches code (`api/index.py`, `worker/http_entry.py`, NullPool support, eager-Celery path); compose stack also exists for self-hosting | Consistent |
| D2 | AGENT_HANDOFF: "frontend is only a Next.js stub (`apps/web`)"; docker_setup.md lists a Next.js frontend service on :3000 | Real product frontend is `apps/landing` (Vite React; builds cleanly); `apps/web` is indeed a stub without package.json; `docker/frontend/Dockerfile` is dead Next.js config; compose has NO frontend service | Stale docs; two conflicting frontend narratives |
| D3 | AGENTS.md/README: strict MyPy enforcement | `pyproject.toml` sets `disallow_untyped_defs = false`; mypy passes but is not strict | Overstated |
| D4 | Auth docs imply permission-scoped endpoints via `require_permission` everywhere | `require_permission(permission)` ignores the permission string entirely - it only verifies authentication (apps/backend/authz.py). Real role enforcement exists only via `ProjectAuthorizationService` on project-scoped routes (datasets, orgs, projects) | Material gap - see P1-1 |
| D5 | AGENT_HANDOFF Executor Architecture paths (`executor.py`, `local_executor.py`, `docker_executor.py`) | Verified correct on current main. (An earlier apparent absence during this audit was a wrong-tree artifact: a concurrent process moved the shared worktree to stale local `main` mid-audit; see Unknowns.) | Consistent |
| D6 | AGENTS.md warning about rewritten migrations `3a1cf533642c`, `2256bd2b7c2c` | Those revision IDs do not exist in this branch's `alembic/versions/` (heads: initial baseline, paypal provider, credit-tx index, RLS default-deny, execution attempts, gha_execution_backend) | Warning references history not present on this branch line |
| D7 | README structure omits `cli/`, `sdk/`, empty `services/*` dirs, `apps/admin` | Repo carries many planned-but-unbuilt placeholder surfaces | Incomplete |

---

## 4. Frontend Audit (`apps/landing`)

- **Stack:** React 19, react-router-dom 7, Zustand, Tailwind 4, visx charts, oxlint, vitest (declared), TypeScript ~6.0.
- **API layer:** `src/core/api/client.ts` - single fetch wrapper: base URL from `VITE_API_BASE_URL` (default `http://localhost:8000`), Bearer token from `localStorage['atlas_token']`, `{success,data}` envelope unwrapping, structured `ApiError`, single-flight 401 re-auth (dev-only auto-login using seeded demo credentials; disabled in production builds).
- **Feature-by-feature integration status:**

| Feature | Data source | Evidence |
| --- | --- | --- |
| Auth (login/register/me) | Real API | `authService.ts` -> `/api/v1/auth/*`; envelope matches backend `APIResponse[TokenResponse]` |
| Benchmarks catalog/detail | Real API with silent mock fallback | `benchmarkService.ts` returns `MOCK_BENCHMARKS` with `error:null` on ANY failure or empty list - UI looks alive when backend is down |
| Benchmark creation | Fake | `createBenchmark()` never calls the API; normalizes payload locally and reports success |
| Evaluations/Executions (dispatch, status, cancel, list) | Real API | `evaluationService.ts` matches backend exactly (`POST /benchmarks/{bv}/executions`, `/executions*`, `/executions/dispatch-targets`); maps statuses from the engine's canonical enum; refuses to invent metrics |
| Reports | Real API | `/api/v1/reports/runs`, `/runs/{id}` |
| Agent tasks/providers/reports | Real API (in-process backend execution) | Full task lifecycle incl. approve/cancel/clarify/run-again; README admits agent-in-process is not robust serverless |
| Billing (plans/checkout/capture/payments) | Real API | Stripe/Razorpay/PayPal paths; 2 test suites exist |
| Dashboard | Real API | `GET /api/v1/dashboard` aggregate |
| Datasets catalog/hierarchy/health/governance | Mock-driven | `useDatasetCatalog.ts` imports `mockDatasets` ("In real life, from data source"); service file exists but targets endpoints the backend does not expose (see section 7) |
| Models | Mock-driven | `MOCK_MODELS` in store + hooks |
| Providers | Mock-driven | `MOCK_PROVIDERS`; real data exists at `GET /api/v1/agent/providers` - unwired |
| Experiments | Mock-driven | `MOCK_EXPERIMENTS`; fabricated logs/metrics/stages; no backend concept exposed |
| Leaderboard | Dead code | `getGlobalLeaderboard()` calls `GET /api/v1/leaderboard` which exists nowhere in the backend; function has no consumer |
| History, Search, System, Orgs/Projects | No frontend consumer | Backend routes exist; UI never calls them |

- **Error handling:** services collapse errors into `{data, error}` results; several catch-blocks deliberately return mock data with `error:null` - failures are invisible to users.
- **Tests:** 3 files total (`client.test.ts` + 2 billing suites). Vitest could not execute locally (incomplete `node_modules`; see section 10).

---

## 5. Backend Audit

- **Framework:** FastAPI factory (`main.py`), Pydantic v2, pydantic-settings, SQLAlchemy 2.0 sessions via `Depends(get_db_session)`, structlog, RequestContextMiddleware, custom exception handlers mapping `DomainException`.
- **Routers (all mounted under `/api/v1` unless noted):** auth; organizations (+ members); projects (+ org-scoped listing/creation); datasets (project-scoped CRUD + exports/download); benchmarks (global list/get/update/delete, project-scoped create, versions with validate/publish/archive lifecycle); executions (create per benchmark-version, get, cancel, list, dispatch-targets); history (recent benchmarks/executions/models); internal workers (`/api/v1/internal/workers/acquire|heartbeat|complete_success|complete_failure` - pull-mode worker API); evaluation (`POST /projects/{pid}/executions/{eid}/evaluate`); reporting (runs, run detail, export, model capabilities); search; system (celery health [superuser], liveness, readiness, Prometheus metrics); leaderboard (benchmark/capability views, model summary/history/benchmarks/rank-history, snapshot rebuild); agent (task create/get/list/delete + approve/cancel/clarify/run-again + tools/providers); billing (plans, checkout, capture, webhooks x3, subscriptions, invoices, payments); dashboard; root health. **NOT mounted: `routers/models.py`** (`GET /api/v1/models` from adapter registry).
- **Application layer:** executions flow through `ExecutionApplicationService` -> domain `ExecutionService` -> `SqlAlchemyExecutionRepository`; submission records an outbox `ExecutionQueuedEvent` in the same transaction (outbox pattern honored).
- **Workers:** Celery app with eager mode for brokerless deploys. `tasks.py::run_execution_task` implements backend routing/kill-switch; `outbox_sweep_task` fans events to Execution/Evaluation/Snapshot subscribers; `stale_attempt_reaper` resets stuck attempts; `github_dispatcher` reserves a PENDING attempt (partial unique index = idempotency guard) then fires `repository_dispatch` carrying only opaque UUIDs.
- **AuthN/AuthZ:** HS256 JWT (`/auth/login|register|me`) widely required; `require_permission(...)` appears at ~15 call sites but validates authentication only - the permission string is unused (D4/P1-1). Project-scoped routes enforce org roles via `ProjectAuthorizationService` (real RBAC). Worker `/wake` uses shared bearer token; internal worker acquire API supports pull-based workers.
- **LLM providers:** Gemini/Groq/Mistral/NVIDIA/Ollama adapters + deterministic mock fallback when keys absent; Grok disabled by config.
- **Config:** pydantic-settings with validators; `ENVIRONMENT=production` refuses known dev secrets; `EXECUTION_BACKEND` validated against {docker, github_actions, disabled}; github_actions requires `GITHUB_EXECUTION_TOKEN`.

**Completeness classification:** fully implemented + tested (auth, benchmarks lifecycle, executions/outbox/worker, reporting, leaderboard, dashboard, billing core); implemented but thin (search, history, system); partial/mock-backed (agent in-process execution; LLM mock provider); stub/dead (unmounted models router; 9 empty `services/` directories; `cli/`, `sdk/` placeholders).

---

## 6. Database Audit

- **Engine:** PostgreSQL 15 (Supabase in prod with pooler + RLS default-deny migration; local via compose or SQLite fallback).
- **Schema:** ~60 tables across 12 model modules: tenancy (organizations, members, invitations, projects, configurations+versions); authoring (benchmarks, versions, capabilities, categories, lifecycle state machine); datasets (registry/source/license/version/export actions); tasks (tasks, prompts, test cases, constraints, evaluation rules); execution (adapters+versions, executions, execution_attempts with container provenance + metrics JSONB, model outputs, artifacts); evaluation (strategies+versions, judges, results/details/artifacts, capability profiles/scores); leaderboard snapshots+entries; reporting (reports/versions/metrics); outbox messages; billing (products/prices/features/subscriptions/invoices/payments/refunds/credits/usage/webhook events); audit log; notifications; agent task records.
- **Migrations:** 6 linear revisions including RLS default-deny hardening and `gha_execution_backend` (metrics column + partial unique active-attempt-per-execution index).
- **Access patterns:** Repository pattern respected in execution/benchmark paths; several routers do inline raw queries (executions dispatch-targets/list, create pre-checks, leaderboard) - pragmatic, but query logic leaks into the HTTP layer. Tenant-safety wart: execution creation falls back to "first TestCase dataset_version_id in the entire database" when neither payload nor benchmark primary version provides one (routers/executions.py:113-121) - cross-project data can be silently attached to an execution.
- **Usability by consumers:** backend yes; workers/execution yes (privileged direct session; GHA runner writes results directly through pooled URL); CLI-via-API yes (indirect); CLI-direct technically possible (SQLAlchemy models importable) but would bypass RBAC/RLS/outbox semantics - discouraged.

---

## 7. Frontend <-> Backend Integration (traced flows)

Working end-to-end chains (verified path-for-path against routers):

1. **Login** -> `POST /api/v1/auth/login` -> JWT envelope -> token stored -> `GET /auth/me`. Works.
2. **Benchmark catalog** -> `GET /api/v1/benchmarks` -> paged `BenchmarkRead` -> mapper -> cards. Works (silent mock fallback masks failures).
3. **Dispatch run** -> ensure session -> `GET /executions/dispatch-targets` -> `POST /benchmarks/{bv}/executions` -> outbox event -> worker -> poll `GET /executions/{id}` -> progress from completed/total items -> scores joined from `/reports/runs`. Works - this is the flagship integrated flow, aligned with the engine's status enums.
4. **Reports / Dashboard / Billing / Agent** -> matching routes with envelope-compatible responses. Works.

Broken or fake chains:

| Flow | Break point | Detail |
| --- | --- | --- |
| Datasets page | Client<->API boundary | UI reads `mockDatasets`; service calls flat `/api/v1/datasets[/{id}]` but backend exposes only `/projects/{project_id}/datasets...` -> guaranteed 404; unnoticed because page renders mocks |
| Leaderboard page | Service layer | Calls nonexistent flat `/api/v1/leaderboard`; real endpoints are nested (`/benchmarks/{id}/leaderboard`, `/models/{name}/summary`, ...); service is unconsumed dead code either way |
| Models page | Entirely client-side mocks | Backend models endpoint exists but is unmounted (below) |
| Providers page | Client-side mocks | Provider truth exists at `GET /api/v1/agent/providers` - unwired |
| Experiments page | Entirely client-side mocks | No corresponding backend concept exposed at all |
| Model listing API | Router mounting bug | `routers/models.py` defines `GET /api/v1/models` but `main.py` never includes it (a prior branch fixed mounting: `feature/recover-pr35-integration`; fix absent here) |
| Silent-failure UX | Error philosophy | Multiple services convert exceptions into mock data with `error:null`; polling retries quietly; UI cannot distinguish demo vs real data (evaluations excepted via `config.source` tags) |

CORS, ports, env vars: no mismatches found (`VITE_API_BASE_URL` consistent; CORS configurable). The gaps are contract/routing gaps, not transport problems.

---

## 8. API Inventory

Legend - FeConsumer: frontend usage. Status: Complete / Thin / Dead-or-mocked.

| Endpoint (under `/api/v1` unless noted) | Method | Purpose | FeConsumer | CLI candidate | Status |
| --- | --- | --- | --- | --- | --- |
| `/health` (root, no auth) | GET | Liveness + component summary | no | yes (`atlas health`) | Complete |
| `/auth/register` | POST | Account creation | yes | yes | Complete |
| `/auth/login` | POST | JWT issuance | yes | yes (`atlas login`) | Complete |
| `/auth/me` | GET | Profile | yes | yes | Complete |
| `/organizations`, `/{org_id}`, `/{org_id}/members(+POST)` | GET/POST | Tenancy admin | no | later | Complete |
| `/projects/{project_id}` | GET | Project fetch | no | later | Complete |
| `/organizations/{org_id}/projects` GET/POST | GET/POST | Project listing/creation | no | later | Complete |
| `/projects/{pid}/datasets` GET/POST; `/{dataset_id}` GET | GET/POST | Dataset catalog + creation | service exists but calls WRONG paths (flat); UI uses mocks | yes once flat/alias route or scoping story decided | Complete (backend) |
| `.../datasets/{id}/exports` POST/GET; `/{export_id}` GET/download | GET/POST | Export pipeline | no | yes (`atlas dataset export`) | Complete |
| `/benchmarks` GET | GET | Global benchmark list | yes | yes (`benchmark list`) | Complete |
| `/benchmarks/{id}` GET/PUT/DELETE | CRUD | Benchmark detail/maintenance | get only | yes | Complete |
| `/benchmarks/{id}/versions` GET/POST | Version management | version list/create | no | yes (`benchmark versions`) | Complete |
| `/benchmark-versions/{vid}` PUT; `/validate` `/publish` `/archive` POST | Lifecycle transitions | validation/publication state machine | no | strong CLI fit (`benchmark validate/publish`) | Complete |
| `/benchmarks/{bvid}/executions` POST | Create execution (queues via outbox) | yes | yes (`atlas run`) | Complete |
| `/executions/dispatch-targets` GET | Runnable benchmark versions w/ dataset resolution | yes | yes (`run` preflight) | Complete |
| `/executions` GET (filters: bv, status, limit, offset) | Run history | yes | yes (`run list`) | Complete |
| `/executions/{id}` GET; `/{id}/cancel` POST | Run detail/cancel | yes | yes (`run get/cancel`) | Complete |
| `/history/benchmarks|executions|models/recent` GET | Recent activity | no | nice-to-have | Thin |
| `/internal/workers/acquire|heartbeat|complete_success|complete_failure` POST | Pull-mode worker protocol | no (worker infra) | no (internal) | Complete |
| `/projects/{pid}/executions/{eid}/evaluate` POST | Enqueue evaluation | no | yes (post-run eval) | Complete |
| `/reports/runs` GET; `/runs/{id}` GET; `/runs/{id}/export` GET; `/models/{mid}/capabilities` GET | Reports & capability profiles | yes (first two) | yes (`atlas reports`) | Complete |
| `/search?q=` GET | Global search | no | maybe | Thin |
| `/system/celery/health` (superuser), `/health/live`, `/health/ready`, `/metrics` | Ops/diagnostics | no | yes (`atlas doctor` building blocks) | Complete |
| `/benchmarks/{bvid}/leaderboard` GET (+history); `/capabilities/{cid}/leaderboard` GET(+snapshot POST); `/models/{name}/summary|history|benchmarks|rank-history`; snapshot POSTs | Leaderboards | dead service call to wrong path | yes (`leaderboard show`) | Complete (backend) |
| `/agent/tasks` CRUD + approve/cancel/clarify/run-again; `/tools`; `/providers`; `/reports/{id}` | Agentic assistant | yes | maybe v2 | Complete (in-process execution caveat) |
| `/billing/plans|checkout|capture|webhooks x3|subscriptions|invoices|payments(/{id})` | Monetization | yes (subset) | low priority | Complete |
| `/dashboard` GET | Aggregated stats | yes | maybe (`atlas status`) | Complete |
| `/models` GET (adapter registry) | Available models | NO ROUTER MOUNTED; UI uses mocks | yes (`models list`) once mounted | Dead code |

Duplicated/conflicting APIs: datasets exist both as project-scoped routes (backend truth) and as the flat paths the frontend invented; leaderboards have both a per-benchmark view and a (frontend-assumed) global view that does not exist. No other duplication found.

---

## 9. Execution Infrastructure

Actual mechanics of a run (verified across `routers/executions.py` -> `ExecutionApplicationService` -> outbox -> `worker/tasks.py` -> executors -> DB):

1. `POST /benchmarks/{bvid}/executions` validates benchmark version, resolves dataset version (payload > benchmark primary > **global first-testcase fallback** [wart]), creates `Execution(QUEUED)` + outbox `ExecutionQueuedEvent` in one transaction.
2. Outbox sweep (Celery Beat or the brokerless `outbox_sweep_loop`) dispatches events: ExecutionQueued -> `run_execution_task`; completion -> evaluation; evaluation -> leaderboard snapshots.
3. `run_execution_task` consults `EXECUTION_BACKEND`:
   - `disabled`: returns immediately - execution stays QUEUED forever (kill switch).
   - `github_actions`: `github_dispatcher` reserves a PENDING attempt (partial unique index prevents duplicates), fires `repository_dispatch` with `{execution_id, correlation_id}` only; runner workflow (`benchmark-execute.yml`) validates UUIDs via env vars, builds pinned image, CLAIMS the attempt (`gha-run:<id>` provenance), runs `run_execution_ci.py` -> reaper -> `ExecutionWorker.process()` -> DockerExecutor container -> results/provenance written straight to Atlas DB; bounded retries then FAILED with `termination_reason=dispatch_failed`.
   - `docker`: worker-local DockerExecutor runs the attempt in a hardened container (non-root, read-only fs, dropped caps, resource limits, no socket mounted).
4. Attempt provenance persisted in `execution_attempts` (container id, image digest, exit code, termination reason, CPU/memory/PID/network metrics JSONB, trace ids). ModelOutputs per test case; artifacts recorded.
5. `stale_attempt_reaper` requeues stuck attempts on worker boot/periodically.

Supporting pieces: internal pull-mode worker API under `/api/v1/internal/workers/*` (acquire/heartbeat/complete_*) exists for external workers; Render `/wake` nudge + self-keepalive for free-tier hosting.

Evidence of real-world function: `docs/EXECUTION_PLANE_VALIDATION_REPORT.md` documents a successful GitHub-hosted-runner dry run (2026-08-22) with production code path, containerized execution, provenance persistence, idempotency and zero orphan containers; README section 14 records an end-to-end production run through the full v1 loop.

---

## 10. Existing Test / CI Coverage

Backend (`pytest`):
- `tests/backend/` (~30 files): API contract tests per router (auth/authz/benchmarks/datasets/executions/evaluation/history/leaderboard/reporting/slice2), worker orchestration, executor selection, docker-executor config, execution-backend routing, github dispatcher (UUID hardening, idempotent attempt reservation, token non-leakage), stale-attempt reaper, runner failure/idempotency, login warmup, exporters.
- `tests/api/`: milestone contract suites incl. chaos tests.
- `tests/execution/`: domain/API/persistence/scheduler/worker data-plane suites (must run separately due to a SQLAlchemy mapper-registry collision documented in pyproject testpaths comment - known friction point).
- `tests/integration/`: e2e execution pipelines, live E2E (env-gated), Docker executor integration (real container), agent concurrency, benchmark repository.
- Frontend: 3 vitest files (api client error semantics, billing capture closure, billing refresh sync).

CI (`.github/workflows/test.yml`): ruff check+format, mypy (packages + 4 services), schema init from Alembic, pytest against Postgres 15 service - i.e., CI proves backend->DB on every push/PR to main. Additional workflows: `benchmark-image.yml` (image publish), `benchmark-execute.yml` (production execution), `benchmark-execute-dryrun.yml` (zero-secret validation).

What is NOT proven by automation:
- Frontend <-> backend integration (no e2e/browser tests; frontend tests are pure-unit with mocks; nothing runs SPA against API).
- Frontend unit tests did not even execute locally (vitest missing from installed node_modules).
- Docker image builds could not be verified here (Docker daemon not running on this machine).
- The 4 `test_d7_reporting_async.py` tests require real Postgres (use TRUNCATE) - they error under SQLite; excluded from CI risk but worth noting as PG-only.

GitHub-infra vs repo failures: during this audit GitHub was unreachable from this machine (git fetch failed after ~21s connect timeout). This is an external infrastructure condition, not a repository defect; all conclusions above derive from local refs at 0dd49ec. CI results referenced are from the checked-in validation report, not re-run remotely.

Local verification actually performed (Windows, Python 3.12 venv):

| Command | Result |
| --- | --- |
| `ruff check .` | PASS (all checks) |
| `ruff format --check .` | 708 tracked files formatted; 2 untracked local `scratch/` files would be reformatted (not part of repo) |
| `mypy packages` | PASS - no issues in 231 source files |
| `pytest tests/backend/test_github_dispatcher.py tests/backend/test_execution_backend_routing.py` (throwaway SQLite) | 14 passed |
| `pytest tests/backend` (minus minio/ollama/distributed-infrastructure needing external services; minus d7 PG-only) | **127 passed, 0 failed** |
| `npm run lint` (oxlint, apps/landing) | 0 errors, 87 warnings |
| `tsc -b` (apps/landing) | App source: 0 errors. Test files/vite.config fail only because vitest/@testing-library are absent from the partial node_modules install |
| `vite build` (apps/landing) | SUCCESS (4.5s bundle) |
| `docker ...` | Not runnable - Docker Desktop daemon not started |

Not run, deliberately: full `pytest` against the configured `.env` DATABASE_URL because it points at the remote production Supabase Postgres - running the suite there was judged unsafe; frontend vitest (deps missing).

---

## 11. CLI Boundary Analysis

Option A - CLI -> HTTP API (`/api/v1`)
- Exists today: yes, comprehensively (auth, benchmarks lifecycle, executions, reports, leaderboard, dashboard, health/system diagnostics).
- Create: thin client only (config file, token storage, command mapping).
- Coupling: lowest possible; OpenAPI schema is derivable automatically (`/docs`).
- Auth: user JWT today; machine tokens/PAT-style clients would be new work (P1-2).
- Local dev experience: excellent (uvicorn + sweep loop + SQLite/Postgres).
- Remote usage: native (same API the web app uses; CORS-free since CLI is not a browser).
- Testing: API contract suites already cover most surfaces; CLI tests mock HTTP.
- Compatibility: matches multi-tenancy/RLS/outbox semantics by construction.
- Risks: permission layer is decorative (P1-1) so CLI inherits weak enforcement until fixed; some flows need project context the CLI must supply (datasets, evaluation).

Option B - CLI -> shared application/domain layer (import packages directly)
- Exists: the Python packages are importable (`pip install -e .[dev]` works; mypy-clean).
- Create: a new app shell inside the monorepo plus session/env bootstrap duplicating apps/backend wiring.
- Coupling: high - CLI becomes a second privileged consumer like the worker; every engine refactor must keep two frontends green.
- Auth: bypasses HTTP RBAC entirely; CLI operator effectively gets DB-role privileges.
- Local dev: good; remote: poor (needs DB credentials + network path to Supabase/worker infra - operationally unacceptable for a distributed tool).
- Testing: must duplicate what API contract tests already prove.
- Verdict: appropriate ONLY for a maintainer-only `atlas doctor --local` style deep diagnostic, if ever.

Option C - CLI -> dedicated control-plane service
- Exists: nothing beyond the existing API; internal workers API is the closest thing.
- Create: an entire new service - unjustified while `/api/v1` already centralizes control.
- Verdict: rejected for now; revisit only when multi-cluster execution arrives.

Option D - Hybrid
- Sensible long-term shape: A for all user-facing commands, plus an optional local-mode escape hatch that shells into LOCAL execution mode (outbox sweep + eager Celery) rather than importing domain code - i.e., process boundary, not import boundary. Also note the CLI can reuse `scripts/prod_seed.py`-style entrypoints via subprocess for dev convenience without coupling.

Recommendation: **Option A now, with Option D's process-boundary local mode as a Phase 2/3 nicety.** Evidence: the API is the only surface with auth, tenancy, validation, and contract tests aligned; the frontend proves the API covers the core loop; the execution plane is explicitly designed behind `EXECUTION_BACKEND` routing so a CLI needs zero knowledge of executors - it just submits executions and reads state.

---

## 12. CLI Capability Map

Supported TODAY by existing endpoints (Phase-1 candidates):

| Command sketch | Backing endpoint(s) | Notes |
| --- | --- | --- |
| `atlas login/logout/whoami` | /auth/login, /auth/me | token storage pattern mirrors frontend |
| `atlas config` | local config file (base URL, project/org ids) | new, client-side only |
| `atlas status` / `atlas health` | /health, /system/health/live, /health/ready, /dashboard | readiness includes DB check |
| `atlas benchmark list/get` | /benchmarks, /benchmarks/{id}, versions list | |
| `atlas benchmark validate/publish/archive` | /benchmark-versions/{vid}/validate|publish|archive | lifecycle state machine already enforced server-side |
| `atlas run submit <bv> --model <m> [--dataset <dv>]` | /benchmarks/{bvid}/executions | mirrors frontend dispatch exactly |
| `atlas run list/get/cancel` | /executions* | statuses map to engine enum |
| `atlas run watch <id>` | poll /executions/{id} | client-side loop |
| `atlas evaluate <eid>` | /projects/{pid}/executions/{eid}/evaluate | needs project context |
| `atlas reports list/get/export` | /reports/runs* | export formats available |
| `atlas leaderboard show <bvid>` | /benchmarks/{bvid}/leaderboard(+history) | |
| `atlas dataset list/get` (scoped) | /projects/{pid}/datasets... | requires project flag/context |
| `atlas models list` | /models AFTER mounting fix (P1-3) or /agent/providers today | |
| `atlas doctor` | compose of /health, /system/*, auth probe, dispatch-targets probe | read-only diagnostics |

Requiring NEW backend work before they make sense:
- `atlas init` (bootstrap org/project/user locally or remotely) - org/project APIs exist but no bootstrap flow; decide product intent first.
- `atlas dataset create/import` from files - dataset item ingestion endpoints do not exist yet (only metadata CRUD + exports).
- `atlas logs <run>` - attempt/error data is in DB (error_message, termination_reason) but no aggregated log endpoint; container stdout is not retained.
- `atlas run cancel --graceful` semantics beyond current cancel (which depends on backend reachability of the runner).
- Anything touching billing writes via CLI - possible but inadvisable pre-P1-1 fix.

Should NOT exist yet:
- Direct DB inspection commands (would normalize Option B bypass).
- Executor-level commands (`atlas container prune` etc.) - execution topology is a deployment concern, already owned by worker/reaper/GHA workflows.
- Agent task commands in v1 - in-process agent execution is explicitly fragile in production (README Known Limitations).

---

## 13. Blocking Issues (P0)

None found that make the CLI impossible. The audit found no data-loss, security-breaching-by-design, or architecture-invalidating defects. (The closest calls - decorative permissions and the cross-project dataset fallback - are P1s below because a single-tenant/local CLI phase can proceed while they are fixed.)

## 14. High Priority Issues (P1)

1. **Permission enforcement is cosmetic on global routes.** `require_permission("execution:read")` etc. authenticate but never check the named permission; any valid JWT may cancel any execution or mutate benchmarks. Fix by implementing real permission checks (or replacing with explicit role checks) BEFORE the CLI exposes these verbs to more users/automation. Location: apps/backend/authz.py (`require_permission`), consumers across routers.
2. **No machine-client authentication story.** JWTs come from interactive login; expiry defaults ~60 min; no refresh tokens, PATs, OAuth device flow, or service accounts. A headless CLI needs one of these; also decide whether CLI shares the browser token store format or defines `~/.atlas/credentials`.
3. **Unmounted models router / dead endpoint.** `routers/models.py` is implemented but absent from `main.py` include list - mount it (and reconcile with `GET /agent/providers`) before any CLI `models` command.
4. **Dataset contract split-brain.** Backend is strictly project-scoped; the frontend service (and therefore any naive CLI port) assumes flat `/datasets`. Pick the canonical contract, add aliases or migrate callers, and document it - otherwise the first CLI dataset commands will encode the wrong boundary.
5. **Cross-project dataset fallback in execution creation** (routers/executions.py:113-121): silently attaches an arbitrary project's dataset version. Should 400 instead. Matters more once CLI makes scripted submissions easy.
6. **Silent mock fallback in frontend services** masks backend outages (benchmarkService returning `MOCK_BENCHMARKS` with `error:null`). Not a CLI blocker per se, but it corrupts any future dogfooding signal ("the app works" when API is down) and signals missing integration tests.

## 15. Medium / Low Priority Issues (P2/P3)

P2:
- Frontend has zero e2e coverage; add one smoke path (login -> list -> dispatch -> poll) before CLI work changes contracts.
- `services/` tree mixes real implementations with 9 empty directories - delete stubs or mark planned ownership to reduce confusion (AGENTS.md forbids inventing services, yet empty dirs imply them).
- `tests/execution` cannot share the default pytest run due to mapper-registry collision (documented workaround) - consolidate or isolate properly.
- Inline raw queries in routers (executions list/dispatch-targets, leaderboard) bypass repositories - move to repositories for consistency.
- Docs drift: AGENT_HANDOFF frontend claims, docker_setup.md Next.js references, strict-mypy claim, migration warning referencing nonexistent revisions on this branch line.
- Tracked build artifact churn (`atlas.egg-info/` shows modified between branch switches) - should be untracked/gitignored.

P3:
- oxlint carries 87 warnings; vitest deps not installed in a fresh-ish checkout (partial node_modules) - pin postinstall behavior or document `npm ci`.
- `docker/frontend/Dockerfile` is dead commented-out Next.js config - remove or rewrite for Vite.
- Accept header `application/vnd.atlas.v1+json` is declared but unused server-side.
- `cli/` and `sdk/` placeholder dirs predate any plan - either reserve intentionally in README structure or remove until designed.

## 16. Recommended Next Architecture

**CLI as an API client (Option A), structured to later become a thin SDK:**

```text
atlas CLI (Python, typer/click)            <- new code, lives in cli/
   |
   | HTTPS + JWT (user login now; PAT/device flow at P1-2)
   v
/api/v1  (existing FastAPI - single control plane)
   |
   +- executions/benchmarks/datasets/reports/leaderboard/health
   |
   v
outbox -> workers -> EXECUTION_BACKEND routing -> docker | github_actions | disabled
```

Rationale (evidence-backed):
- The API already proves the full lifecycle the CLI needs; frontend `evaluationService` is effectively a working reference client whose request/response handling a CLI can mirror.
- Execution topology is deliberately hidden behind `EXECUTION_BACKEND`; a CLI that talks to the API survives executor changes (Docker -> GHA -> future K8s/Batch) with zero changes.
- Tenancy/RBAC/RLS semantics are enforced server-side; Option B would bypass them and fork business logic.
- An internal Python package (`cli/` importing only generated/typed API models, or a future `sdk/python`) keeps the door open for the TypeScript SDK placeholder without coupling either to domain internals.

Preconditions to schedule before/with Phase 1 (from section 14): real permission checks (P1-1), machine auth decision (P1-2), mount-or-delete models router (P1-3), dataset contract resolution (P1-4).

## 17. Recommended CLI Phase 1 (smallest useful version - NOT implemented here)

Scope: read-only + submit, against one environment, human auth:

1. `atlas login` / `atlas whoami` (JWT in OS keychain or `~/.atlas/`, mirroring frontend token semantics).
2. `atlas config set url/project` (per-profile config file).
3. `atlas health` (/health + /system/health/ready).
4. `atlas benchmark list/get`, `atlas benchmark versions <id>`.
5. `atlas run submit/list/get/cancel/watch` (mirror of the proven frontend dispatch flow).
6. `atlas reports list/get`.
7. `atlas doctor` (auth probe, health, dispatch-targets reachability).

Explicitly out of scope for Phase 1: dataset mutation, agent commands, billing writes, local execution mode, machine accounts (pending P1s). This set requires **zero new backend endpoints**, so it cannot destabilize the web app while it lands.

## 18. Unknowns

- Live GitHub state: fetch was impossible during the audit; origin/main conclusions rest on locally cached refs (0dd49ec). If remote main advanced past PR #50 today, deltas are unaccounted for.
- Production claims (README v1 E2E verification, Render/Vercel/Supabase deployment health, GHA run 32581407965) were taken from committed reports, not independently reproduced.
- Full pytest suite was not executed end-to-end (production Supabase URL configured in `.env` made that unsafe from this machine); CI-green status for the exact audited commit is therefore inferred from validation docs + local subset (127 passed), not proven.
- Frontend vitest suites could not execute locally (missing dev dependencies in node_modules); they pass/fail unknown.
- Docker builds/compose bring-up unverified (daemon not running).
- `apps/admin` was not examined in depth.
- A concurrent process moved this shared working tree from `audit/cli-readiness` back to stale local `main` mid-audit (reflog 09:42:25); it was switched back and all affected reads were re-verified on the correct tree, but if other sessions are active, treat any snapshot of this repo as time-sensitive.

---

*End of audit. No CLI implementation accompanies this report, per phase instructions.*


