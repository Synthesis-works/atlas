# Production Execution Plane Audit & Design

**Branch:** `feature/docker-execution-runtime`
**Date:** 2026-08-21
**Status:** Design audit only. **No infrastructure was deployed or modified.**

---

## 0. Evidence Standard

Every claim below is tagged:

- **[VERIFIED]** — read directly from source code / config in this repo.
- **[REPORTED]** — from live-infrastructure observations supplied by the operator (Render logs, Supabase data). Not independently re-verified by this agent.
- **[RECOMMENDATION]** — architectural proposal requiring a decision before implementation.

---

## 1. Current Topology [VERIFIED]

### 1.1 Control plane

| Component | Host | Evidence |
|---|---|---|
| FastAPI API | Vercel | `apps/backend/main.py`; operator report |
| PostgreSQL | Supabase | `DATABASE_URL` env; operator report |
| Frontend | Vercel (`apps/landing`) | `docs/docker_setup.md` |

### 1.2 Worker (the problem)

`apps/backend/worker/http_entry.py` [VERIFIED]:

- Runs `outbox_sweep_loop.main()` in a background thread.
- Polls the outbox table every `OUTBOX_POLL_INTERVAL` seconds (default 5s).
- With `CELERY_TASK_ALWAYS_EAGER=true`, every downstream Celery task — including `run_execution_task` → `ExecutionWorker.process()` → `ExecutionRunner.run()` — executes **inline in the same Python process**.
- Exposes `GET /health` and bearer-authenticated `POST /wake`.
- Self-pings `WORKER_PUBLIC_URL` while a sweep is active because **Render Free spins instances down after ~15 minutes of no inbound traffic** [VERIFIED in code comments; behavior REPORTED].

Consequence: today's production executes benchmarks as ordinary Python inside a shared, internet-facing worker process with full access to process environment (including all secrets). The Docker isolation boundary does not exist there yet.

### 1.3 What the current Render service cannot do [VERIFIED by architecture]

- A Render *native-runtime* Python service has no Docker daemon and no privilege to create containers. There is no `docker.sock`, no DinD sidecar, and Render does not expose privileged mode on native runtimes.
- Therefore `DockerExecutor.is_available()` will return `False` and execution will fail explicitly with `ExecutorUnavailable` — which is the designed, correct behavior ("no silent fallback").

---

## 2. Proposed Topology [RECOMMENDATION]

```text
CONTROL PLANE (trusted)
  Vercel API ──► Supabase Postgres ──► outbox table
        │                                  │
        │ POST /wake (bearer)              │ poll / claim
        ▼                                  ▼
EXECUTION PLANE (privileged host, dedicated)
  Docker-capable worker service
    ├─ outbox sweep loop (existing code, unchanged)
    ├─ ExecutionRunner → ExecutorRegistry.get_default() → DockerExecutor
    │      │
    │      ▼
    │  Docker Engine (host daemon, NOT DinD)
    │      └─ one ephemeral benchmark container per attempt
    │             └─ egress-only network → LLM providers
    └─ writes ModelOutputs + ExecutionAttempt provenance back to Supabase
```

Key separation principle: the **runner host is privileged infrastructure**; the **benchmark container is the untrusted boundary**. The control plane never receives Docker privileges; the benchmark container never receives DB credentials or the Docker socket.

---

## 3. Hosting Options for the Docker-Capable Worker

### Option A — Render Docker runtime service running the worker *as* a container [VERIFIED capability]

Render supports Docker-based services (builds from a `Dockerfile`). However, a container on Render still has **no access to a Docker daemon** for sibling containers. Running Docker-in-Docker requires `--privileged`, which Render does not offer.

**Verdict:** ❌ Cannot host `DockerExecutor` sibling-container launches. Suitable only if we later swap `DockerExecutor` for a remote-Docker-API client pointing at an external engine (adds latency + a network-exposed Docker API — not recommended).

### Option B — Smallest viable: single cloud VM ("execution runner") [RECOMMENDED]

One small Linux VM (e.g., Hetzner CX22 ≈ €4/mo, DigitalOcean basic droplet ≈ $6/mo, AWS Lightsail ≈ $5–10/mo) running:

- Docker Engine (official install)
- The existing Atlas worker via `docker/backend/Dockerfile` image, launched with the compose `worker` command (or `http_entry.py` for keepalive parity)
- Mounted `/var/run/docker.sock` **into the worker container only** (socket-mount pattern), OR run the worker directly on the host via systemd

Trade-offs:
- You operate patching/uptime of one VM.
- Full Docker Engine available → `DockerExecutor` works unchanged.
- Cheapest option that satisfies the security model.

Socket-mount note [RECOMMENDATION]: mounting `docker.sock` into the worker container grants it root-equivalent power **on that VM only**. This is acceptable precisely because the VM is already designated privileged execution infrastructure; the untrusted boundary remains the benchmark container, which never sees the socket.

### Option C — Fly.io Machines / AWS ECS / Kubernetes Jobs

Fly Machines can run privileged-ish workloads; ECS/Fargate supports task-level isolation natively (each attempt = one Fargate task; would use a future `AwsBatchExecutor`-style backend rather than `DockerExecutor`). K8s gives strongest long-term story but highest complexity.

**Verdict:** defer. The `Executor` interface already leaves room for these; do not pay this cost now.

### Decision requested

Adopt **Option B** (single VM runner) as Phase-B target. Estimated infra cost: **$5–10/month**, plus negligible Supabase/Vercel deltas.

---

## 4. Job Routing: How Benchmark Work Reaches the Runner [VERIFIED mechanics]

No new queue is needed. The existing flow already works if the runner simply replaces the current Render worker:

1. API commits `Execution(QUEUED)` (+ outbox row) to Supabase.
2. Runner's `outbox_sweep_loop` polls the same table over Supabase's pooled connection string.
3. Sweep dispatches `run_execution_task` → eager mode executes inline → `ExecutionWorker.process()` → `ExecutionRunner.run()` → registry resolves `DockerExecutor` (because `ENVIRONMENT=production`) → container launch.
4. Results/provenance are written back through the same SQLAlchemy session.

Two config changes make this correct [RECOMMENDATION]:
- Set `ENVIRONMENT=production` on the runner so `get_executor_for_environment()` returns `"docker"` (already implemented in `apps/backend/worker/tasks.py`).
- Keep `CELERY_TASK_ALWAYS_EAGER=true` initially (single-runner topology); revisit a real Redis broker only when scaling beyond one runner.

Wake integration: point `WORKER_WAKE_URL` at the runner's `/wake` endpoint instead of the Render URL. If the runner is a private VM, either expose `/wake` behind a bearer token + TLS (it already enforces bearer auth) or drop wake entirely and rely on the 5s poll (simplest; recommended first).

---

## 5. Networking Requirements

| Path | Direction | Requirement |
|---|---|---|
| Runner → Supabase | outbound 5432/TLS | Pooled connection string (Supabase pooler, IPv4-compatible) |
| Runner → Docker Hub/GHCR | outbound 443 | Pull `ATLAS_BENCHMARK_IMAGE` |
| Benchmark container → LLM providers | outbound 443 | **Must be allowed** |
| Inbound to runner | none required (poll model) | Only if keeping `/wake`: expose minimal HTTPS endpoint |

⚠️ **Defect found during this audit [VERIFIED]:** `DockerExecutor` originally hard-coded `network_mode="none"` with no configuration hook. **RESOLVED:** executor now resolves network mode as explicit argument → `ATLAS_BENCHMARK_NETWORK` env → `"none"` (secure default unchanged; covered by `tests/backend/test_docker_executor_config.py`). Production launches set `ATLAS_BENCHMARK_NETWORK=bridge` (or a dedicated egress-only Docker network).

---

## 6. Secrets & Environment Variables

### Runner service needs [VERIFIED names from `apps/backend/config.py`]

```
ENVIRONMENT=production            # selects DockerExecutor
DATABASE_URL=<supabase-pooler-url>
CELERY_TASK_ALWAYS_EAGER=true     # single-runner phase
WORKER_AUTH_TOKEN=<shared secret> # only if /wake kept
ATLAS_BENCHMARK_IMAGE=ghcr.io/<org>/atlas-benchmark-runner:<tag>
ATLAS_BENCHMARK_NETWORK=bridge    # pending §5 change
LOG_LEVEL=INFO
```

LLM provider keys (`GEMINI_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`, …) are needed **by the benchmark container**, not just the runner. Today they would flow through `ATLAS_EXECUTION_PAYLOAD`/env injection in `DockerExecutor._build_container_config`.

### What the benchmark container must NEVER receive [VERIFIED enforced in code]

- `DATABASE_URL` / any Supabase credential
- `/var/run/docker.sock`
- JWT secret, billing keys (Stripe/Razorpay/PayPal)
- Host filesystem paths

**RESOLVED:** `DockerExecutor._provider_env()` now injects only an explicit allow-list (`GEMINI_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) sourced from the runner env at launch time — never baked into the image, never written to disk, never persisted to the DB. A regression test asserts DB/JWT/billing secrets can never appear in container env.

---

## 7. Benchmark Image: Build, Version, Publish [RECOMMENDATION]

New file (not yet created): `docker/benchmark/Dockerfile`

```dockerfile
FROM python:3.11-slim
# deps only for adapter HTTP calls; NO db drivers, NO docker SDK
RUN pip install --no-cache-dir httpx
RUN adduser --system --uid 10001 sandbox
COPY packages/execution_engine/container_entry.py /app/
COPY apps/backend/adapters /app/apps/backend/adapters/
COPY apps/backend/worker/prompt_resolver.py /app/apps/backend/worker/
COPY packages/llm /app/packages/llm/
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
USER sandbox
CMD ["python", "-m", "packages.execution_engine.container_entry"]
```

Versioning/publishing:
- Build in GitHub Actions on merge to main → tag `sha-<git-sha>` + rolling `latest`.
- Push to GHCR (private repo ⇒ configure a fine-grained pull token on the runner).
- Record the resolved **digest** at pull time; `DockerExecutor` already captures `image_digest` into provenance when populated — extend `is_available()` to store `client.images.get(...).id` digest [small follow-up].

---

## 8. Results, Logs, Artifacts Return Path [VERIFIED current state]

Already functional end-to-end for structured results:

- `ModelOutput` rows → `model_outputs` table (per test case).
- Provenance → `benchmark_execution_attempts` (container id, exit code, termination reason, CPU/mem/PID/net stats, trace ids) — migration applied locally; **must also be applied to Supabase prod schema before rollout** [BLOCKER, see §12].
- Container stdout logs: currently parsed for JSON-lines outputs then discarded.

**Recommendation:** persist raw container logs as an `Artifact(type=LOG)` row (table exists) pointing at object storage (Supabase Storage or MinIO, both already used in-repo). Keep payload ≤ some cap (e.g., 1 MB tail). Defer streaming logs.

---

## 9. Failure / Retry / Cleanup Behavior [VERIFIED]

- Celery task retries ×3 with exponential backoff; dead-letter log after max retries.
- Each retry creates a **new** `ExecutionAttempt` row (attempt_number increments) — history preserved.
- Container cleanup is in a `finally` block with `remove_container(force=True, v=True)`; leak test (`test_container_cleanup_on_error`) verifies zero leaked containers even on failure.
- Timeout path: `api.wait(timeout=...)` → exit 137/124 mapping → `termination_reason ∈ {timeout, oom}` recorded.
- Runner crash mid-run: attempt stays `RUNNING` until a future lease/reaper pass closes it. **Known gap** — acceptable for Phase B v1; the existing `execution_leases` concept in `packages/execution_engine` is the natural home for a reaper later.

---

## 10. Security Model Summary

| Layer | Control | Status |
|---|---|---|
| Benchmark container | non-root UID, read-only rootfs, cap-drop ALL, no-new-privs, mem/cpu/pids limits, tmpfs-only writes, no socket, no DB creds | ✅ implemented + tested |
| Egress | default `none`; `ATLAS_BENCHMARK_NETWORK` hook implemented, prod sets egress-only network | ✅ code done; prod config pending |
| Runner host | dedicated VM, only place holding docker.sock + provider keys | 📋 Option B decision |
| Control plane | zero Docker privileges; talks only via DB + optional bearer `/wake` | ✅ by construction |
| Secrets | provider keys injected at launch via allow-list only, never in image/DB | ✅ implemented + tested |
| Supply chain | pinned base image, digest capture, GHCR private | ⚠️ CI pipeline to build |

Residual risks to accept consciously: kernel attack surface shared with runner host (mitigate: keep VM minimal, enable unattended upgrades, consider gVisor later); provider-key exfiltration by a malicious benchmark workload is possible by design since adapters need them — scope keys per-model where providers support restricted keys.

---

## 11. Migration Steps (ordered, each independently verifiable)

1. Apply `benchmark_execution_attempts` migration to Supabase prod (additive only).
2. Approve + implement §5 egress-network change and §6 key allow-list (both small, tested).
3. Add `docker/benchmark/Dockerfile` + GitHub Actions build/publish (§7).
4. Provision Option B VM; install Docker; deploy worker image with §6 env.
5. Point `WORKER_WAKE_URL` (optional) at runner; otherwise rely on polling.
6. Run one shadow execution against a mock/test dataset; verify attempt row shows real `container_id` + digest from prod runner.
7. Flip production executions to the runner; retire the Render Python worker (keep as cold fallback only if desired — but note it will correctly refuse work with `ExecutorUnavailable` once `ENVIRONMENT=production`).

---

## 12. Remaining Blockers

| # | Blocker | Type |
|---|---|---|
| 1 | Prod Supabase lacks `benchmark_execution_attempts` table | Schema migration needed |
| 2 | ~~`DockerExecutor` hard-codes `network_mode="none"`~~ | ✅ RESOLVED — `ATLAS_BENCHMARK_NETWORK` hook + tests |
| 3 | ~~Provider-key injection not scoped~~ | ✅ RESOLVED — allow-list injection + tests |
| 4 | No benchmark image build pipeline | CI work (§7) |
| 5 | Runner VM not provisioned | Infra decision (§3 Option B) |
| 6 | Image-digest capture not persisted from pull-time metadata | Small follow-up |
| 7 | Stale-attempt reaper absent | Accepted gap v1 (§9) |

---

## 13. Verified-Facts Recap

- Render native Python worker cannot launch sibling containers; current prod executes inline with `CELERY_TASK_ALWAYS_EAGER=true` [VERIFIED code + REPORTED live logs].
- Local `DockerExecutor` is real-container verified: container `52d478665121`, image `python:3.11-alpine`, exit 0, telemetry + cleanup proven by 10 passing integration tests [VERIFIED this branch].
- All isolation flags are enforced in `_build_container_config` and covered by tests [VERIFIED].
- The only structural code gaps between "works locally" and "works in prod" are items 2–4 in §12.
