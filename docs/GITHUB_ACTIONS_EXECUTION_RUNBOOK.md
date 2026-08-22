# GitHub Actions Execution Runbook

Atlas's first production execution backend. **Status: experimental MVP** —
deliberately chosen for ₹0 budget to learn real-world behavior, NOT permanent
infrastructure. The executor abstraction (`packages/execution_engine`) means a
future router (Oracle VM / Kubernetes / AWS Batch) can replace it without
touching benchmark logic.

## Architecture

```text
Atlas (Render)                        GitHub                       Runner (ubuntu-24.04)
--------------                        ------                       ---------------------
execution QUEUED
  -> outbox sweep
  -> run_execution_task
      EXECUTION_BACKEND=github_actions
  -> create PENDING attempt   ----->  POST /repos/{repo}/dispatches
     (partial unique index =          event: benchmark-execution
      duplicate-dispatch guard)       payload: {execution_id, correlation_id}
                                              |
                                              v
                                     benchmark-execute.yml:
                                       validate UUID -> uv sync ->
                                       build image -> CLAIM attempt ->
                                       run_execution_ci.py ->
                                         reaper -> ExecutionWorker.process()
                                           -> DockerExecutor -> container
                                           -> results + provenance -> DB
                                       -> cleanup check
```

The workflow writes results directly to the Atlas database; the Render worker
never executes benchmarks itself in this mode.

## Enablement / Kill switch

| `EXECUTION_BACKEND` | Behavior |
| --- | --- |
| `docker` | Run benchmarks on the worker's own Docker daemon (default) |
| `github_actions` | Dispatch to GitHub-hosted runners |
| `disabled` | **Kill switch**: new executions stay QUEUED forever, never executed locally |

- Changing the value requires only a Render environment-variable update +
  service restart — no redeploy.
- If dispatch retries are exhausted, the execution is marked `FAILED`
  with termination reason `dispatch_failed`; it never falls back to local.
- In-flight runs continue if the switch is flipped; cancel them via
  `gh run cancel <run-id>` or let them finish.

## Required secrets / configuration (manual setup)

GitHub (repo Synthesis-works/atlas → Settings → Secrets and variables → Actions):

| Secret | Purpose |
| --- | --- |
| `PROD_DATABASE_URL` | Supabase Postgres URL (pooler). Driver-side only; never enters containers |
| `PROD_JWT_SECRET` | Satisfies production-mode Settings guard on the runner |
| `GEMINI_API_KEY` etc. | Provider keys, optional per benchmark; reach containers only via `_provider_env` allow-list |

Atlas (Render backend + worker services):

| Env var | Value |
| --- | --- |
| `EXECUTION_BACKEND` | `github_actions` (or `disabled` to kill) |
| `GITHUB_EXECUTION_TOKEN` | Fine-grained PAT: repository = Atlas only, permission **Actions: Read and write**, Contents: read |
| `GITHUB_EXECUTION_REPO` | `Synthesis-works/atlas` (default) |

## Observability map

Diagnose an execution end-to-end from its Atlas id:

```text
execution_id
  -> executions row (status)
  -> benchmark_execution_attempts (latest):
       executor_type='github_actions'
       worker_id='gha-run:<run_id>'        <- set by claim step
       metrics JSONB:
         runner, gh_run_id, gh_run_url,
         image_build_ms, execute_ms, driver_total_ms
       container_id / image_digest / exit_code /
       cpu_seconds / peak_memory_bytes      <- written by docker_executor
  -> https://github.com/Synthesis-works/atlas/actions/runs/<run_id>
```

Structured log events (searchable in GH Actions logs): `github_dispatch_attempted`
(status_code, latency_ms), `CI execution starting/finished` (total_ms),
reaper summaries at driver startup.

Latency stages currently measured: dispatch latency (Atlas log), image build
(`IMAGE_BUILD_MS`), execution (`EXECUTE_MS`), driver total. Queue latency =
attempt.created_at → started_at (claim time); runner allocation latency is not
directly observable from inside the job (known limitation).

## Diagnosis flow

1. Execution stuck QUEUED? Check Render logs for `Execution dispatch suppressed`
   (kill switch) or repeated `GitHub dispatch failed`.
2. Attempt PENDING but no `gha-run:` in worker_id? The workflow never claimed:
   check whether a run exists for the dispatch (Actions tab); if missing, the
   dispatch was lost — the reaper will close the attempt after the stale window
   and requeue.
3. Run failed? Read the failing step: validation → build → claim → execute.
4. Container-level failure: attempt row has exit_code/termination_reason;
   full logs inside the run's "Execute via production code path" step.

## Known quirks (living list)

- `repository_dispatch`/`workflow_dispatch` only work for workflows on the
  default branch — feature branches cannot be dispatched directly (hit during
  Level-3 validation; dry-run used scoped push triggers instead).
- Dispatch API returns HTTP 204 with no run id; correlation is established by
  the claim step writing `gha-run:<id>` back onto the attempt.
- No direct signal for runner-allocation delay; observed via total latencies.
- Public repo ⇒ all run logs are publicly visible; this is why prompts/outputs/
  credentials must never appear in argv or logs (enforced by design).
- Standard runners: 4 vCPU / 16 GB / 6 h job cap; org-level concurrency limits
  may queue jobs during peaks.
- Workflow `timeout-minutes: 70` is intentionally above the driver's internal
  runtime cap so the driver classifies timeouts before GitHub kills the job.
- Cancellation: `executions.cancellation_requested` is honored by the worker
  between phases; a running GH job is not force-cancelled from Atlas yet.

## Rollback procedure

1. Set `EXECUTION_BACKEND=disabled` on Render (+ restart). New executions stop
   dispatching immediately.
2. Optionally cancel in-flight runs: `gh run list --workflow=benchmark-execute.yml`
   then `gh run cancel <id>`.
3. Reaped/requeued executions remain safe: nothing executes locally while the
   switch is off (regression-tested).
