# Atlas — LLM Execution & Evaluation Platform

Atlas is a distributed platform for benchmarking large language models. You author versioned datasets and benchmarks, execute them against real LLM providers, evaluate the responses against reference solutions, and get reports and leaderboards — all through a clean web UI and a REST API, with a production stack that runs unattended on free cloud tiers.

It is currently deployed as **Atlas v1** on Vercel (web + API), Supabase (PostgreSQL), and Render (worker) — and the full loop (web → API → database → outbox → worker → real LLM → evaluation → reports → leaderboard) has been verified end-to-end against live production.

> **Project status: v1 production baseline.** The current production deployment has passed a real end-to-end execution and evaluation test. See [docs/releases/v1.0.0.md](docs/releases/v1.0.0.md) for the preserved snapshot.

---

## 1. What Atlas is

### The problem

Evaluating an LLM properly is a chore: datasets live in ad-hoc scripts, benchmark definitions drift between runs, execution and evaluation are bolted together, and results cannot be compared across models or reproduced later.

### What Atlas does

Atlas gives you a single, reproducible pipeline:

1. **Author** datasets and compose them into benchmarks, each with an immutable version.
2. **Execute** the benchmark against real LLM providers (Gemini, Groq, Mistral, NVIDIA NIM, local Ollama, and more) through one consistent API.
3. **Evaluate** every model response against reference checks (prompt + reference based, similarity/LLM-judge style scoring).
4. **Report** results as metrics, reports, and live leaderboards — persisted and queryable, not printed to a terminal.

### What makes it different

- **Immutability by design** — datasets and benchmarks are versioned; every run is reproducible and traceable.
- **Outbox-driven execution** — work is recorded in a transactional outbox and processed by a worker; no lost tasks, no fragile in-process scheduling.
- **Works on free tiers** — the full production deployment runs on Vercel + Supabase + Render free plans, with the same engine usable locally or on a persistent VM.
- **Multi-tenant from day one** — organizations, projects, and fine-grained RBAC on every resource.

## 2. Current v1 capabilities

| Capability | Description |
|---|---|
| Benchmark authoring & versioning | Compose datasets into benchmarks; immutable versions (`dataset_versions`, `benchmark_versions`) for reproducibility. |
| Datasets | Versioned dataset authoring with items and prompt templates. |
| Model execution | Deterministic execution of a benchmark against a target model, with retries and attempt tracking. |
| Evaluation | Reference-based evaluation per item (evaluation engine with pluggable strategies, plus LLM-judge style checks via the agent tooling). |
| Metrics | Execution and evaluation metrics collected per run. |
| Reports | Auto-generated reports on completion (HTML/Markdown export available). |
| Leaderboards | Snapshot-based leaderboards rebuilt on every completed run. |
| Agent | An agentic assistant layer (tools for datasets, benchmarks, execution, evaluation) with Gemini / Groq / Mistral backends and provider failover. |
| Authentication / RBAC | JWT authentication, permission-scoped endpoints, admin/user roles. |
| Multi-tenant orgs & projects | Full RBAC isolation across organizations and projects. |
| Real LLM providers | Gemini, Groq, Mistral, NVIDIA NIM, Ollama (local); see [Providers](#llm-providers). |
| Local execution mode | Full pipeline on one machine — no Redis, no external broker. |

## 3. Production architecture

Atlas v1 is deployed as four cooperating pieces:

```text
Atlas Web (Vercel)          - React SPA, talks only to the public API
        ↓ (HTTPS, JWT)
Atlas API (Vercel)          - FastAPI, serverless functions, privileged DB role
        ↓
Supabase PostgreSQL         - single source of truth + RLS + outbox table
        ↓ (outbox rows)
Atlas Worker (Render)       - eager Celery worker, polls the outbox
        ↓
LLM Providers               - Gemini / Groq / Mistral / NVIDIA / Ollama
        ↓
Evaluation / Reports        - evaluation pipeline + leaderboard snapshots
        ↓
Supabase                    - results persisted
```

Key mechanisms:

- **RLS** — row-level security is enabled on the schema (default-deny for backend-only tables) so the frontend's `anon` role cannot reach backend tables directly.
- **JWT auth** — the API issues HS256 JWTs; every `/api/v1` endpoint beyond auth is permission-scoped.
- **Supabase pooler** — the serverless API connects through the Supabase connection pooler (`:6543`, transaction mode) with `NullPool` for short-lived serverless connections; migrations and the long-lived worker use the direct Postgres endpoint.
- **Vercel serverless API** — FastAPI packaged for Vercel Python functions (`maxDuration: 300`), single entrypoint (`api/index.py`).
- **Render worker** — a long-lived process on Render free: an HTTP entrypoint (`/health` public, `/wake` bearer-authenticated) plus the outbox sweep loop with `CELERY_TASK_ALWAYS_EAGER=true`, so every downstream task runs inline without a broker.
- **Outbox-driven execution** — each execution inserts an `ExecutionQueuedEvent` into the outbox **in the same transaction** as the execution row. The worker sweeps the outbox (`FOR UPDATE SKIP LOCKED`), so no task is ever lost.
- **Worker wake mechanism** — after commit, the API sends a fire-and-forget `POST /wake` (bearer `WORKER_AUTH_TOKEN`) to the worker so it processes work immediately instead of waiting for the next poll. While a sweep is running, the worker pings its own public URL (`WORKER_PUBLIC_URL`) to keep the free-tier instance awake through the run.

## 4. Execution modes

The same execution/evaluation engine runs in three modes:

| Mode | How | When to use |
|---|---|---|
| **LOCAL** | Outbox sweep loop process (`python -m apps.backend.worker.outbox_sweep_loop`) with eager Celery | Development; future privacy/max-control deployments |
| **CLOUD** | Vercel API + Render worker (current public deployment) | Zero-ops public hosting on free tiers |
| **PERSISTENT VM** | Existing systemd unit (`deploy/worker/atlas-worker.service`), e.g. Oracle Cloud or any Linux VM | Longer-lived, cheaper throughput, larger models, future enterprise/self-hosted installs |

All three share the identical outbox → execution → evaluation → reporting pipeline; only the host differs.

## 5. Technology stack

- **Language / runtime**: Python 3.11+ (production on 3.12), Node.js for the frontend
- **API framework**: FastAPI + Pydantic v2 + pydantic-settings
- **Data access**: SQLAlchemy 2.0 (Repository pattern), Alembic migrations
- **Database**: PostgreSQL 15 via Supabase (managed), local via Docker
- **Orchestration**: transactional outbox + Celery tasks with eager execution on the worker (Redis broker optional, not required)
- **Hosting**: Vercel (web + API serverless), Render (worker), Supabase (Postgres + pooler + RLS)
- **Frontend**: Vite + React + TypeScript, oxlint, visx charts, SPA rewrites
- **LLM providers** (execution engine, `packages/llm`): Gemini (`GEMINI_API_KEY`), Groq (`GROQ_API_KEY`), Mistral (`MISTRAL_API_KEY`), NVIDIA NIM (`NVIDIA_API_KEY`), Ollama (local, `OLLAMA_HOST`); Grok (`XAI_API_KEY`) available but disabled until models are re-validated
- **Agent providers**: Gemini / Groq / Mistral with mock fallback (`apps/backend/agent`)
- **Quality**: ruff (lint + format), mypy (strict), pytest (Postgres-backed CI)

## 6. Repository structure

```text
apps/
  backend/            FastAPI application: routers/, agent/, worker/
    worker/           celery_app, tasks, outbox_sweep_loop, http_entry (Render), wake_client
  landing/            Vite + React + TypeScript frontend (deployed as atlas-web)
packages/
  database/           SQLAlchemy models, session/engine, Alembic migrations (alembic/)
  execution_engine/   execution pipeline (dispatch, runners, adapters)
  evaluation_engine/  evaluation strategies and scoring
  llm/                provider clients + registry (gemini, groq, mistral, nvidia, ollama)
  benchmark/, datasets/  benchmark & dataset domain logic
  auth/               auth helpers and RBAC primitives
  core/               shared utilities
services/             domain services (execution-service, evaluation-service, dataset,
                      report, search, leaderboard, …)
deploy/
  worker/             systemd unit (persistent VM mode) + Render deployment notes
docs/                 handoffs, project state, implementation history, runbook, releases/
scripts/              prod_seed.py (canonical demo seed), experiment/demo helpers
tests/                pytest suites
```

The most important areas: `apps/backend/worker` (execution engine hosting), `packages/database/alembic` (schema — the single source of truth), `packages/llm` (provider integration), and `apps/landing` (frontend).

## 7. Local development

Prerequisites: Python 3.11+, Node.js 20+, and a PostgreSQL 15 (Docker Compose is easiest; plain Postgres works too). **Redis is not required.**

### 1) Backend environment

```bash
git clone https://github.com/Synthesis-works/atlas.git && cd atlas
python -m venv .venv
.venv\Scripts\activate        # Windows   (POSIX: source .venv/bin/activate)
pip install -e ".[dev]"       # installs all packages + dev tooling
```

> **Note on uv:** the repository ships a `uv.lock`, but the public PyPI `atlas-db` package conflicts with the local `atlas_db` namespace; a plain `uv sync` will install the wrong package and break imports. The verified path above (`pip install -e ".[dev]"`) is what CI uses. A fix for the lockfile source pinning is tracked for a future change.

### 2) Database

```bash
docker compose up -d db        # postgres:15-alpine on localhost:5432 (atlas/atlas)
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/atlas"   # adjust per OS
$env:PYTHONPATH = "packages/database"
python -m alembic -c packages/database/alembic.ini upgrade head
```

Optional demo data (canonical seed, idempotent):

```bash
$env:PYTHONPATH = "packages/database"
python scripts/prod_seed.py
```

### 3) Backend API

```bash
$env:CELERY_TASK_ALWAYS_EAGER = "true"
uvicorn apps.backend.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>

### 4) Local worker

```bash
$env:CELERY_TASK_ALWAYS_EAGER = "true"
python -m apps.backend.worker.outbox_sweep_loop
```

This polls the outbox every 5s and runs the whole downstream pipeline (execution, evaluation, reports, leaderboard) inline — the full LOCAL execution mode with zero brokers.

### 5) Frontend

```bash
cd apps/landing
npm ci
npm run dev        # http://localhost:5173
```

Create `apps/landing/.env.local` with `VITE_API_BASE_URL=http://localhost:8000`.

### 6) Tests & lint

```bash
ruff check . && ruff format --check .
mypy packages
pytest            # needs DATABASE_URL pointing at a Postgres test DB
```

CI (`.github/workflows/test.yml`) runs ruff, mypy, schema initialization from Alembic, and pytest against a Postgres 15 service.

## 8. Production deployment

Current production topology:

| Component | Where | Role |
|---|---|---|
| `atlas-web` | Vercel | React SPA (`apps/landing`), SPA rewrites, public |
| `atlas-api` | Vercel | FastAPI serverless (`api/index.py`, maxDuration 300), public API at `https://atlas-api-synthesis-works.vercel.app` |
| `atlas-worker` | Render | Outbox sweep + eager execution, public health at `https://atlas-worker-9e37.onrender.com/health`, `/wake` protected by bearer token |
| Supabase project | Supabase | PostgreSQL, RLS applied, pooler (`:6543`) for the API, direct connection for migrations/worker |

Deployment notes:

- **API**: Vercel project auto-deploys from `main`. Requires `ENVIRONMENT=production` (the app refuses to boot with the dev `JWT_SECRET`), `CORS_ORIGINS` (JSON list including the web origin), `DATABASE_URL` = Supabase pooler (transaction mode), `DATABASE_POOL_CLASS=null`, and `WORKER_WAKE_URL` + `WORKER_AUTH_TOKEN` for the wake mechanism.
- **Worker**: Render service from branch `main`, command `python -m apps.backend.worker.http_entry`, port from `$PORT`. Set `CELERY_TASK_ALWAYS_EAGER=true`, `WORKER_AUTH_TOKEN` (same value as the API), `WORKER_PUBLIC_URL`, and the LLM keys. Configure a health check path of `/health`. Full checklist in [deploy/worker/README.md](deploy/worker/README.md).
- **Database**: apply migrations with `PYTHONPATH=packages/database python -m alembic -c packages/database/alembic.ini upgrade head` against the direct Supabase endpoint; run `scripts/prod_seed.py` once to seed the demo user and benchmarks.

## 9. Environment variables

Names only — values are secrets or per-deployment and are never committed.

**Frontend (`apps/landing`, public)**

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Base URL of the deployed Atlas API (browser-facing, public) |

**API (`apps/backend`, Vercel)**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Supabase pooler URL (transaction mode), privileged role |
| `DATABASE_POOL_CLASS` | `null` for serverless (NullPool) |
| `ENVIRONMENT` / `DEBUG` / `APP_NAME` / `LOG_LEVEL` | Runtime configuration; `production` guards dev secrets |
| `JWT_SECRET` | HS256 signing secret (must be unique in production) |
| `JWT_ACCESS_EXPIRE_MINUTES` | Access token lifetime (default 60) |
| `CORS_ORIGINS` | JSON list of allowed browser origins |
| `WORKER_AUTH_TOKEN` | Bearer token the API sends to the worker `/wake` |
| `WORKER_WAKE_URL` | Worker wake endpoint (post-commit nudge) |
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `MISTRAL_API_KEY` | Agent provider keys |
| `GEMINI_MODEL` / `GROK_MODEL` / `MISTRAL_MODEL` / `LLM_PROVIDER_TIMEOUT` | Provider model overrides |
| `ARTIFACT_BASE_DIR` | Evaluation artifact output directory |
| `STRIPE_*` / `RAZORPAY_*` | Optional billing keys (disabled when unset) |

**Worker (`apps/backend/worker`, Render / VM)**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Direct Supabase Postgres URL, privileged role |
| `CELERY_TASK_ALWAYS_EAGER` | `true` — run all downstream tasks inline, no broker |
| `OUTBOX_POLL_INTERVAL` / `OUTBOX_BATCH_SIZE` | Outbox sweep tuning |
| `WORKER_AUTH_TOKEN` | Must match the API value (validates `/wake`) |
| `WORKER_PUBLIC_URL` | Worker's own public URL, pinged while work is running (free-tier keepalive) |
| `RENDER_KEEPALIVE_INTERVAL_SECONDS` | Keepalive interval (default 300) |
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `MISTRAL_API_KEY` / `NVIDIA_API_KEY` | Execution provider keys |
| `LOG_LEVEL` / `ENVIRONMENT` | Runtime configuration |

**Local development (`.env` at repo root)**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Local Postgres (default `sqlite:///./atlas.db`; use Postgres for parity) |
| `CELERY_TASK_ALWAYS_EAGER` | `true` for the no-broker local worker |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Only if running a real broker (optional) |
| `JWT_SECRET` | Dev default is accepted when `ENVIRONMENT != production` |
| LLM keys (above) | Optional; without them the mock provider is used |

## 10. Security

- **JWT authentication** — HS256 tokens, configurable expiry, required on all `/api/v1` routes except auth and health.
- **RBAC** — endpoints are permission-scoped (`require_permission`); organizations/projects provide tenant isolation.
- **RLS** — Supabase row-level security is enabled with default-deny on backend-only tables, so the frontend's public `anon` role cannot read or write backend data directly.
- **Privileged DB connections** — both the API and the worker connect with a privileged role; they are backend-only and never exposed to the browser.
- **Worker bearer authentication** — the `/wake` endpoint requires `WORKER_AUTH_TOKEN` (401 otherwise); `/health` is deliberately public.
- **Secrets never committed** — all secrets are environment variables; only names/descriptions are documented.
- **Frontend/public vs backend secrets** — `VITE_API_BASE_URL` is the only frontend variable; everything else lives server-side.

## 11. Known limitations

- **Render free tier** — cold starts on first request (~30–90 s); the instance sleeps after ~15 min idle; a free instance that is killed mid-run leaves the execution `RUNNING` (no automatic recovery reset yet).
- **Single worker, serial execution** — one worker processes outbox tasks serially; scale-out is future work.
- **Serverless API limits** — Vercel functions cap at 300 s; anything long-running must happen in the worker.
- **Agent tasks in production** — agent requests run in-process on the API background thread, which a serverless instance may terminate with the request; agent task execution in production is not yet robust. The agent is safe for short interactions.
- **Grok provider disabled** — models are deprecated/unauthorized on the current account; re-enabling is tracked.
- **Cosmetic UI issues** — the execution list `completed_items` counter can lag the true output count for runs that report results in batches; status and results are accurate.
- **Provider list on API** — the providers dropdown reflects keys present on the API instance; set LLM keys there too if you want it populated.

## 12. Roadmap

- **Persistent VM deployment** — run the existing systemd worker on Oracle Cloud or any Linux VM for cheaper, always-on throughput.
- **Local/private execution mode** — the LOCAL mode as a productized option for privacy-sensitive workloads.
- **Enterprise/self-hosted execution** — packaged installs with the same engine.
- **Stronger worker recovery** — heartbeats, stuck-run reset, resume-after-kill.
- **Additional evaluation capabilities** — more strategies, LLM-judge refinements, human-in-the-loop review.
- **Improved artifact storage** — move artifacts from the worker disk to Supabase Storage/S3.
- **Multi-worker scale-out**, queue priorities, and richer leaderboard UI.

## 13. Quick start / demo

Live demo (public, free tier — allow for cold starts):

- Web: <https://atlas-web-synthesis-works.vercel.app>
- API: <https://atlas-api-synthesis-works.vercel.app> (OpenAPI at `/docs`; health at `/health`)
- Worker health: <https://atlas-worker-9e37.onrender.com/health>

Demo credentials (seeded by `scripts/prod_seed.py`): `demo@atlas.val` / `password123`

To see the full loop in minutes:

1. Log in at the web app (or `POST /api/v1/auth/login`).
2. Open **Benchmarks** → pick **MBPP** (or HumanEval) → **Run** with model `groq/openai/gpt-oss-20b` (a small, fast model; needs `GROQ_API_KEY` on the worker).
3. Watch the execution progress; on completion the leaderboard and reports update with real results.

## 14. Project status

Atlas is at **v1** — feature-complete for the core loop above. The current production deployment (Vercel + Supabase + Render) has passed a real end-to-end test: a single execution submitted through the public API was processed through the outbox, executed against a real LLM provider, evaluated, reported, and snapshot to the leaderboard — with exactly one execution record, no duplicates, and all outbox events processed.

The v1 baseline is preserved as a git tag for recovery (see [docs/releases/v1.0.0.md](docs/releases/v1.0.0.md) for the exact commit).

## License

Copyright (c) 2026. All rights reserved.
