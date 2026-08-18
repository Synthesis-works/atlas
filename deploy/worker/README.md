# Atlas Persistent Worker

The persistent worker drains the outbox table and runs the full
execution -> evaluation -> report pipeline that cannot run in Vercel's
request-scoped serverless functions.

```
Vercel API (writes outbox rows)  ->  Supabase  ->  this worker (drains outbox)
```

## What it runs

```
python -m apps.backend.worker.outbox_sweep_loop
```

with `CELERY_TASK_ALWAYS_EAGER=true`, which executes every downstream task
(execution, evaluation, report) inline in this process — the same pipeline the
local one-click environment uses.

## Required environment (in `/opt/atlas/.env`)

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Supabase **session pooler** connection string (`:5432`) |
| `CELERY_TASK_ALWAYS_EAGER` | yes | must be `true` |
| `OUTBOX_POLL_INTERVAL` | no | seconds between sweeps (default `5`) |
| `GROQ_API_KEY` | yes (Groq) | LLM provider for real executions |
| `GEMINI_API_KEY` / `XAI_API_KEY` / `MISTRAL_API_KEY` / `OPENAI_API_KEY` / `NVIDIA_API_KEY` | optional | other providers |
| `ARTIFACT_BASE_DIR` | no | artifact base dir (default `/var/lib/atlas/artifacts`) |
| `LOG_LEVEL` | no | `INFO` / `DEBUG` |
| `JWT_SECRET` | no | unused by the worker, set anyway for safety |
| `ENVIRONMENT` | no | leave unset or `development` |

Do NOT commit this file. Secrets live only in the environment system.

## Setup (Ubuntu / Oracle Cloud Always Free, or any Linux host)

```bash
# 1. Create the atlas user and directories
sudo useradd --system --create-home --shell /usr/sbin/nologin atlas || true
sudo mkdir -p /opt/atlas
sudo chown atlas:atlas /opt/atlas

# 2. Install uv (https://docs.astral.sh/uv/) as the atlas user, then:
cd /opt/atlas
git clone https://github.com/Synthesis-works/atlas.git .
uv sync                      # or: python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env         # then fill in the production values above

# 3. Install and start the service
sudo cp deploy/worker/atlas-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now atlas-worker

# 4. Watch it
journalctl -u atlas-worker -f
```

## Testing from a laptop first (recommended)

The same commands work on a laptop (skip systemd; run the loop in a terminal).
This validates the whole production architecture against Supabase before
provisioning a permanent host.

```powershell
# Windows (PowerShell), from the repo root
$env:DATABASE_URL="postgresql://..."   # session pooler string
$env:CELERY_TASK_ALWAYS_EAGER="true"
python -m apps.backend.worker.outbox_sweep_loop
```

## Verification

- Start a benchmark run from the Atlas web UI.
- Confirm the worker logs the outbox sweep, then execution progress
  (`Execution <id> progress: n/total`), then evaluation and report rows.
- Confirm the run reaches `COMPLETED` in the UI.

## Render Free (Web Service) deployment

Render Free cannot run a separate "Background Worker", but a free **Web
Service** can host this process as long as it binds `$PORT`. The
`http_entry.py` module wraps the existing sweep loop unchanged:

```
python -m apps.backend.worker.http_entry
```

It runs `outbox_sweep_loop.main()` in a background thread and serves:

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /health` | none | Render health check / liveness |
| `POST /wake` | `WORKER_AUTH_TOKEN` bearer | immediate outbox sweep; the API calls this after committing an execution |

### Wake flow

1. The API creates an execution (outbox row committed).
2. The API fire-and-forgets `POST {WORKER_WAKE_URL}` with `WORKER_AUTH_TOKEN`
   bearer auth. Submission succeeds even if the worker is asleep/unreachable
   and the wake is never sent before the DB commit.
3. The worker wakes (cold start ~30-90s), sweeps, and runs the pipeline.

### Render's 15-minute idle spin-down and the keepalive

Render Free spins an instance down after **15 minutes of no inbound traffic**.
Outbound polling does not count. Mitigation implemented in `http_entry.py`:

- While a sweep is in progress (`outbox_sweep_loop.sweep_active`), the worker
  pings its own public URL (`WORKER_PUBLIC_URL`) every
  `RENDER_KEEPALIVE_INTERVAL_SECONDS` (default 300s). Inbound traffic keeps the
  instance awake for the whole run, and the pings stop the moment there is no
  work, so an idle worker still sleeps.

**Honest limitations (free tier):**

- If `WORKER_PUBLIC_URL` is missing or the instance is killed mid-run for
  another reason (deploy, OOM, crash), the in-flight execution is terminated.
  The outbox message remains `PENDING` and will be re-swept on the next wake,
  but `ExecutionWorker.process` only runs executions that are still `QUEUED`,
  so a killed run is left in `RUNNING` with no automatic recovery in the
  current architecture. The keepalive prevents this in the normal case, but a
  free-tier instance is not an always-on VM.
- Cold starts add ~30-90s latency to the first run after idle.
- One instance, one job at a time; the outbox `FOR UPDATE SKIP LOCKED` sweep
  plus the `QUEUED`-status guard prevent duplicate executions on wake storms.

### Render dashboard settings

- New Web Service -> connect the repo -> root directory: `.`
- Runtime: Python 3.12
- Build command: `pip install -r requirements.txt`
- Start command: `python -m apps.backend.worker.http_entry`
- Instance type: Free
- Health check path: `/health`

### Render environment variables

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Supabase **session pooler** connection string (`:5432`) |
| `CELERY_TASK_ALWAYS_EAGER` | yes | must be `true` |
| `OUTBOX_POLL_INTERVAL` | no | seconds between sweeps (default `5`) |
| `WORKER_AUTH_TOKEN` | yes | must match the API's value; guards `POST /wake` |
| `WORKER_PUBLIC_URL` | yes | own public `/health` URL; enables the keepalive |
| `RENDER_KEEPALIVE_INTERVAL_SECONDS` | no | keepalive pings while busy (default `300`) |
| `GROQ_API_KEY` | yes (Groq) | LLM provider for real executions |
| `GEMINI_API_KEY` / `MISTRAL_API_KEY` / `NVIDIA_API_KEY` / `XAI_API_KEY` / `OPENAI_API_KEY` | optional | other providers |
| `LOG_LEVEL` | no | `INFO` / `DEBUG` |

The API additionally needs `WORKER_WAKE_URL` (e.g.
`https://atlas-worker.onrender.com/wake`). Do NOT commit secrets; set them in
the Render dashboard.

### Testing this locally first

```powershell
# Windows (PowerShell), from the repo root — run the wrapper instead of the loop
$env:DATABASE_URL="postgresql://..."   # session pooler string
$env:CELERY_TASK_ALWAYS_EAGER="true"
$env:WORKER_AUTH_TOKEN="test-token"
$env:PORT="8001"
python -m apps.backend.worker.http_entry
# GET  http://localhost:8001/health            -> 200
# POST http://localhost:8001/wake (no token)   -> 401
# POST http://localhost:8001/wake (Bearer test-token) -> 200
```
