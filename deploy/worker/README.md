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
| `ATLAS_ARTIFACT_DIR` | no | artifact base dir (default `/var/lib/atlas/artifacts`) |
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
