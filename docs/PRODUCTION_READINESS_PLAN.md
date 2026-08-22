# Production Readiness Implementation Plan

**Branch:** `feature/docker-execution-runtime`
**Date:** 2026-08-21
**Status:** PLAN ONLY. Nothing in this document has been executed against production.
**Predecessor:** `docs/PRODUCTION_EXECUTION_PLANE_AUDIT.md` (design accepted)

---

## Ground Rules (binding)

- ❌ No commit, no push, no deploy, no production migration, no infra provisioning as part of this plan.
- ✅ Every step below is written so a human can execute it manually, or explicitly authorize the agent to execute it.
- Steps are tagged: **[AGENT]** = agent can do locally on this branch after approval; **[HUMAN]** = requires account/credential/billing access the agent must never hold.

---

## 1. Benchmark Image — Exact Requirements

### Runtime dependency audit [VERIFIED by import analysis]

`container_entry.py` imports exactly:

```
apps.backend.adapters.factory   → apps/backend/adapters/{__init__,base,factory,mock,real}.py
apps.backend.worker.prompt_resolver
packages.llm.*                  → packages/llm/** (clients, models, config, exceptions, registry)
```

Third-party imports across that closure [VERIFIED via grep]:

| Package | Used by | In image? |
|---|---|---|
| `httpx` | all LLM clients, `real.py` | ✅ required |
| `pydantic` | `packages/llm/models/*` | ✅ required |
| DB drivers | **none** | ❌ excluded |
| provider SDKs | **none** (clients are raw httpx) | ❌ excluded |
| docker SDK | **none** | ❌ excluded |

### Dockerfile spec — `docker/benchmark/Dockerfile` [AGENT, not yet created]

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim@sha256:<pin>        # pin digest at CI time, see §2

RUN adduser --system --uid 10001 --home /sandbox sandbox
WORKDIR /sandbox

COPY packages/execution_engine/container_entry.py /app/packages/execution_engine/
COPY apps/backend/adapters/                        /app/apps/backend/adapters/
COPY apps/backend/worker/prompt_resolver.py        /app/apps/backend/worker/
COPY packages/llm/                                 /app/packages/llm/

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER sandbox
CMD ["python", "-m", "packages.execution_engine.container_entry"]
```

Properties:
- Non-root UID 10001; writable space comes only from executor tmpfs mounts (`/tmp`, `/workspace`) — image rootfs stays read-only.
- No secrets at build time; keys injected at launch via `_provider_env()` allow-list.
- Size estimate ≈ 130–160 MB (slim base + httpx/pydantic).
- Local verification command (agent-executable): build, then run with `network_mode=none` and a mock target to prove entrypoint works offline.

### Known gap to fix before build [AGENT]

`container_entry.py` does `sys.path.insert(0, "/app")` and imports `packages.execution_engine.container_entry` as a module — the COPY layout above satisfies both. However `apps/backend/adapters/__init__.py` and `apps/backend/__init__.py`, `apps/__init__.py` namespace files must be included (COPY of directories covers them). Verify with an offline smoke run.

---

## 2. CI Workflow — Build & Publish with Immutable Digests [AGENT to author, HUMAN to merge]

New file `.github/workflows/benchmark-image.yml`:

```yaml
name: Benchmark Image
on:
  push:
    branches: [main]
    paths: ['docker/benchmark/**', 'packages/llm/**',
            'apps/backend/adapters/**', 'apps/backend/worker/prompt_resolver.py',
            'packages/execution_engine/container_entry.py']
permissions: { contents: read, packages: write }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/benchmark/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/atlas-benchmark-runner:sha-${{ github.sha }}
            ghcr.io/${{ github.repository }}/atlas-benchmark-runner:latest
          provenance: true
```

Digest handling strategy:
1. Runner pulls by **tag**, immediately resolves immutable digest via `client.images.get(tag).id`.
2. Digest is recorded into `ExecutionProvenance.image_digest` → `benchmark_execution_attempts.image_digest` (column already exists).
3. Follow-up hardening (post-MVP): store last-known-good digest in runner env (`ATLAS_BENCHMARK_IMAGE_DIGEST`) and pass `daemon=True` pull-by-digest so rollouts are explicit.
4. GHCR package visibility: private; runner authenticates with a fine-grained PAT or `docker login` stored in `/etc/docker` config on the VM [HUMAN creates token].

Rollback = redeploy previous digest. `latest` is convenience-only, never trusted.

---

## 3. Supabase Migration — Exact Impact (DO NOT APPLY YET) [HUMAN approves, then HUMAN or AGENT-with-temporary-credentials applies]

File: `packages/database/alembic/versions/add_benchmark_execution_attempts.py` (already on branch).

Impact statement:
- **Creates:** enum type `attempt_status` (8 values); table `benchmark_execution_attempts` (28 columns listed in migration).
- **FKs:** `execution_id → executions.id ON DELETE CASCADE`; `created_by_id`/`updated_by_id → users.id ON DELETE SET NULL`.
- **Index:** `ix_benchmark_execution_attempts_execution_id` (non-unique).
- **Additive only.** No existing table/column is altered or dropped. Zero downtime risk; rollback is clean (`downgrade()` drops index, table, enum in reverse order).
- Supabase note: apply via SQL editor or `alembic upgrade head` from a machine holding the **direct** (non-pooled, IPv4) DB URL; Supabase's PgBouncer transaction pooler can break DDL migrations. Recommended: run `alembic upgrade head` once from the operator laptop with `DATABASE_URL` pointed at Supabase, then verify `\dt benchmark_execution_attempts` and `SELECT unnest(enum_range(NULL::attempt_status));`.

Pre-flight checks before applying [AGENT prepares script, HUMAN runs]:
1. Confirm prod head is `7d4a9c2f6e81` (`alembic current`).
2. Confirm `executions` and `users` tables exist with UUID PKs (they do per models).
3. Take a Supabase backup/snapshot (one-click) beforehand.

---

## 4. Docker Runner VM — Exact Requirements

Derived from `DockerExecutor` defaults (2 CPU / 2 GB / 100 PIDs per container, 30-min timeout):

| Resource | Minimum | Recommended | Rationale |
|---|---|---|---|
| vCPU | 2 | 4 | worker process (~0.5 core) + N concurrent benchmark containers × their CPU cap |
| RAM | 4 GB | 8 GB | OS+Docker ~1 GB; worker ~0.5 GB; containers capped at 2 GB each ⇒ 4 GB host supports concurrency 1–2 safely; 8 GB supports 3 |
| Disk | 20 GB SSD | 40 GB | base images (~0.5 GB), benchmark image (~0.16 GB), logs, SQLite-free state |
| OS | Ubuntu 24.04 LTS | same | unattended-upgrades, long support |
| Docker | ≥ 27.x Engine | latest stable | `--pids-limit`, tmpfs options, stats API v1.4x all supported |
| Network | outbound 443 (GHCR, LLM providers), 5432 (Supabase pooler TLS) | — | no inbound ports required (poll model) |

Concurrency model: outbox sweep processes sequentially today ⇒ effective concurrency 1 ⇒ **2 vCPU / 4 GB VM is sufficient for MVP**. If parallelism is added later, cap workers ≤ floor((RAM−1.5GB)/2GB).

Candidate providers (cheapest first): Hetzner CX22 (~€4/mo), DigitalOcean s-2vcpu-4gb ($18/mo — pricier but familiar UI), Oracle Cloud free tier ARM (4 OCPU/24 GB, $0 — availability varies). **Decision deferred until §1–§3 done.**

Firewall: default-deny inbound; allow SSH from operator IP only. No inbound needed for polling mode; if `/wake` kept, front it with Caddy/TLS + bearer token (already enforced in code).

Env/secrets on VM (from §6 of audit): `ENVIRONMENT=production`, `DATABASE_URL` (pooler), `CELERY_TASK_ALWAYS_EAGER=true`, `ATLAS_BENCHMARK_IMAGE`, `ATLAS_BENCHMARK_NETWORK=bridge`, provider keys, optional `WORKER_AUTH_TOKEN`. Stored in `/etc/atlas/runner.env`, `chmod 600 root:root`; systemd `EnvironmentFile=`.

---

## 5. Runner ↔ Supabase Auth & Secret Isolation [VERIFIED mechanics]

- Runner connects with the **same pooled `DATABASE_URL`** the Render worker uses today (Supavisor session/transaction pooler, TLS). No new DB user strictly required; recommended hardening: create a dedicated `atlas_worker` Postgres role with CRUD on `executions`, `model_outputs`, `outbox*`, `benchmark_execution_attempts` only — no superuser, no auth schema.
- Secret flow to containers: runner process env → `_provider_env()` allow-list filter → container env at `create_container` time. Verified by regression test that DB/JWT/billing values can never appear in container env. Secrets are never written to disk, image layers, or DB rows.
- Provider-key least privilege: where providers support restricted/scoped API keys (Gemini, Mistral), issue keys limited to inference scope for the runner.

---

## 6. Runner Lifecycle: Start, Restart, Stale Recovery

**Process management [RECOMMENDATION]:** systemd unit `atlas-runner.service`:

```ini
[Service]
User=atlas
EnvironmentFile=/etc/atlas/runner.env
ExecStart=/opt/atlas/.venv/bin/python -m apps.backend.worker.http_entry
Restart=always
RestartSec=5
# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/run/docker.sock   # socket proxy alternative below
```

Note: `http_entry.py` works unchanged on the VM (health endpoint optional there; keepalive self-ping becomes a no-op when `WORKER_PUBLIC_URL` unset — verified in code).

Socket exposure choice: mounting `/var/run/docker.sock` directly is simplest; safer option is a **docker-socket-proxy** sidecar exposing only `POST /containers/create|start|wait|remove`, `GET /logs|stats|json` — deny image-build and exec. Recommended for MVP: direct socket on a single-purpose VM; proxy as follow-up.

**Stale attempt recovery [KNOWN GAP, plan]:** if the runner dies mid-run, attempts stay `RUNNING`. MVP mitigation: on startup, runner executes a reaper query — any `benchmark_execution_attempts` row with `status IN ('CONTAINER_CREATED','RUNNING')` and `updated_at < now() - interval '45 minutes'` gets marked `FAILED`, `termination_reason='runner_restarted'`, and its execution returns to the queue. Implemented as a small function in `executor_init.py` [AGENT, post-approval]. Docker-side orphans are covered because containers are created without `--restart` and die with the daemon; startup sweep also prunes exited containers labeled `atlas.benchmark=true` (label to be added in `_build_container_config` [AGENT]).

---

## 7. Image Pull / Update Strategy

- Pull policy: at each `is_available()`, `images.get(tag)`; on miss → `images.pull(tag)`. Add daily `docker image prune -f --filter "until=168h"` cron on VM to bound growth.
- Updates: new main-branch merge publishes `sha-<sha>` + moves `latest`. Runner picks up `latest` on next cold start; running executions keep their resolved digest in provenance. For deterministic rollouts, set `ATLAS_BENCHMARK_IMAGE` to a pinned `sha-<sha>` tag in `runner.env` and bump it deliberately [HUMAN decision per release].
- Safety: image contains no secrets; compromise impact = code-level only. Optional future: cosign signature verification before launch.

---

## 8. Minimal Deployment Runbook (decision point)

### Phase 0 — local, zero cost [AGENT, needs your go-ahead]
1. Create `docker/benchmark/Dockerfile` + offline smoke test (§1).
2. Author `benchmark-image.yml` workflow (§2) — merged later with PR.
3. Write stale-reaper + container label patch (§6) + tests.
4. Prepare `scripts/preflight_prod_migration.sql` checks (§3).
5. Commit branch work locally when you say so; open PR. **No push without instruction.**

### Phase 1 — schema [HUMAN]
6. Review migration diff → Supabase snapshot → run `alembic upgrade head` against prod → verify. *(Agent may run this ONLY with a temporary, revocable DB credential you create and delete after.)*

### Phase 2 — image pipeline [HUMAN account actions; AGENT verifies]
7. Merge PR → Actions builds GHCR image → confirm digest published.

### Phase 3 — VM [HUMAN billing/account; AGENT provides exact commands]
8. Provision 2 vCPU/4 GB Ubuntu 24.04 VM → install Docker → deploy runner per §5/§6 → run one mock-target shadow execution → verify `benchmark_execution_attempts` row shows real `container_id` + digest.

### Phase 4 — cutover [HUMAN]
9. Point production executions at runner; retire Render worker service (or leave stopped).

**$0 interim option:** Phases 1–2 + run the runner on your own PC (Docker Desktop already verified working here) with prod `DATABASE_URL` — validates the full loop before spending anything. Risk: home IP/network reliability; acceptable for a validation week.

---

## Open Decisions Required From You

1. Approve Phase 0 items (agent-executable, local-only)?
2. VM budget/provider preference — or start with the $0 home-PC validation?
3. Dedicated `atlas_worker` DB role now or reuse existing URL for MVP?
4. Pin `ATLAS_BENCHMARK_IMAGE` to `sha-<sha>` tags (recommended) or ride `latest`?
