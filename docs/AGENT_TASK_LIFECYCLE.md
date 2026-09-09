# Atlas Agent Task Lifecycle (Event-Driven Resume)

Status: implemented on `feature/agent-event-driven-resume`. This document is
the normative reference for how an agent task survives asynchronous benchmark
execution without holding a serverless function open.

## Problem

With the GitHub Actions execution backend, a benchmark run legitimately takes
30-90+ seconds (runner provisioning + Docker execution). The Vercel API is a
serverless function with `maxDuration: 300`; holding the agent loop open to
wait for remote runs exceeds the platform budget and hard-kills the process
without cleanup (observed in production 2026-08-23: task `d44c63ca…` orphaned
`PENDING` while its execution completed successfully). Waiting is therefore an
orchestration concern, not a reasoning concern, and must not consume the
request lifecycle.

## State machine

```text
PENDING → PLANNING → EXECUTING (RUNNING)
    │  run_benchmark returns DISPATCHED (default; AGENT_INLINE_EXECUTION_WAIT=false)
    ▼
WAITING_FOR_EXECUTION                 ← persisted snapshot; function ENDS here
    │  outbox sweep delivers Execution{Completed|Failed|Cancelled}Event
    │  (atomic claim: WAITING_FOR_EXECUTION → RESUMED)
    ▼
RESUMED → EVALUATING → REPORTING → COMPLETED

Failure branches (task.status = FAILED with error_detail prefix):
    EXECUTION_FAILED       any tracked execution FAILED (authoritative DB read)
    EXECUTION_CANCELLED    any tracked execution CANCELLED
    EXECUTION_TIMED_OUT    any tracked execution TIMED_OUT
    AGENT_RESUME_FAILED    resume task exhausted retries / reclaim limit
    AGENT_RESUME_TIMEOUT   stale-WAITING recovery: still non-terminal past deadline
                           (also reaps orphaned PENDING/EXECUTING rows)
```

Parking is the default because this process never executes benchmark runs
itself — the worker does, regardless of `EXECUTION_BACKEND` (docker or GitHub
Actions alike). Set `AGENT_INLINE_EXECUTION_WAIT=true` only for in-process
eager execution (unit tests of the inline waiter): the PR #54 inline
`wait_for_runs` phase then remains active with its sanctioned-wait invariant
exemption.

## Components

| Concern | Implementation |
|---|---|
| Persisted continuation state | `agent_task_records.snapshot` (full `AgentTask.model_dump`) — plan, observations, trace, execution_ids, counters. Loader: `AgentTask.model_validate(snapshot)`. New fields: `waiting_since`, `resume_count`. |
| Park transition | `AtlasAgent.run_task` loop, post-`run_benchmark` DISPATCHED hook (`apps/backend/agent/agent.py`), gated on `not settings.agent_inline_execution_wait`; traces `AGENT_TASK_WAITING`. |
| Resume trigger | `AgentTaskResumeSubscriber` registered in `outbox_sweep_task`'s `CompositeEventPublisher` (`apps/backend/worker/tasks.py`). Enqueue-only; no DB work in the subscriber. |
| Resume executor | `resume_agent_task` Celery task + `resume_agent_task_core` / `handle_terminal_execution_event` / `recover_stale_waiting_tasks` in `apps/backend/worker/agent_resume.py`, running on the Render worker (eager inline Celery; no broker required). |
| Idempotency | Conditional claim `status == 'WAITING_FOR_EXECUTION'` flips to `RESUMED` exactly once per task. Duplicate completion events, outbox redeliveries, and racing sweeps no-op via `NOT_CLAIMED`. |
| Multi-execution gating | A task resumes only when ALL tracked executions are terminal; authoritative outcome is read from the `executions` table, never trusted from the event payload. Partial-failure tasks stay WAITING until the last run settles. |
| Lost-event safety net | `recover_stale_waiting_tasks` runs inside every outbox sweep: all-terminal WAITING rows are resumed (event raced ahead of persist or was lost); non-terminal rows past `AGENT_STALE_WAITING_MINUTES`/wait deadline are force-failed `AGENT_RESUME_TIMEOUT`; crashed `RESUMED` rows older than 10 min are re-claimed up to `MAX_RESUME_ATTEMPTS = 3`, then failed `AGENT_RESUME_FAILED`; orphaned `PENDING`/`EXECUTING` rows (process died before any checkpoint persist) older than the wait window are force-failed so they stop rendering as live. |

## Sequence

```text
User → Vercel API → POST /agent/tasks
  Vercel function: agent loop … run_benchmark → DISPATCHED
  status := WAITING_FOR_EXECUTION (persisted) → function exits
      │
      ▼
GitHub repository_dispatch → runner → docker → ExecutionWorker.process
      └─ writes ExecutionCompletedEvent to outbox_messages (same txn as COMPLETED)
      │
      ▼
Render worker: outbox_sweep_task
      ├─ OutboxDispatcher.sweep → AgentTaskResumeSubscriber → resume_agent_task.delay
      │     └─ claim → RESUMED → rebuild AgentTask from snapshot →
      │        synthesize terminal observations → continue loop →
      │        evaluate_run → generate_report → COMPLETED (persisted)
      └─ recover_stale_waiting_tasks(db)   # safety net every sweep
```

## Initial-run durability and cross-instance routing

The pre-park phase (create → plan → run_benchmark dispatch) can also take many
LLM cycles. Two hardening layers ship with the persisted store:

- **Cross-instance reads/mutations**: every agent route (`GET`, `cancel`,
  `approve`, `clarify`, `run-again`, `delete`) resolves the task from the
  `agent_task_records` snapshot — the persisted row is the source of truth and
  is rehydrated on every read (`_load_agent_task`), refreshing the
  process-local working copy. A task created or parked on instance A can be
  mutated and read from instance B, and same-instance reads never return a
  stale in-memory copy that the worker (running in another process) has since
  moved on. The registry is only working memory.
- **Durable loop execution**: `AGENT_TASKS_CELERY_EXECUTION=true` (prod
  recommendation) changes the initial/clarify/approve/run-again dispatch: the
  router writes an `AgentRunRequestedEvent` transactional-outbox row in the
  same DB transaction as the task mutation (no broker on the serverless side),
  and the Render worker's `outbox_sweep_task` — via the `AgentRunSubscriber`
  in `apps/backend/worker/agent_tasks.py` — enqueues `run_agent_task` on the
  worker's own broker. This replaces the old FastAPI `BackgroundTasks` thread
  (which a serverless instance may freeze once the response is sent) and the
  earlier direct `run_agent_task.delay(...)` from the API (which silently
  no-ops without a broker). The worker checkpoints `instance_id` +
  `heartbeat_at` onto `agent_task_records` with every persist (migration
  `add_agent_task_execution_tracking`). Default remains `false` so local dev
  and unit tests keep the in-process path. The event-driven resume half
  (`resume_agent_task`) has always run on Celery, so both halves are now
  co-located on the durable worker.

## Deployment prerequisites

- Render `atlas-worker` env must include the reasoning provider keys used by
  resumed runs (at minimum `GEMINI_API_KEY`; add fallback provider keys as
  configured). Without them resume fails with provider errors and the task
  ends `FAILED` after retries.
- Optional tuning: `AGENT_STALE_WAITING_MINUTES` (default 15),
  `AGENT_EXECUTION_WAIT_DEADLINE_SECONDS` (default 480, unchanged).
- **P0 auth hardening**: every `/api/v1/agent/*` endpoint requires a valid
  Bearer JWT. Task reads/mutations are owner-scoped to `claims.sub`
  (`created_by_user_id` stamped at creation; legacy owner-less rows never
  surface), and `/reports/{id}` requires active membership in the
  organization owning the report's execution lineage.
- Optional per-user abuse limits (disabled by default so local dev and tests
  stay deterministic): `AGENT_RATE_LIMIT_ENABLED=true` (prod),
  `AGENT_RATE_LIMIT_MAX_PER_MINUTE` (default 120),
  `AGENT_RATE_LIMIT_MAX_TASKS_PER_DAY` (default 200). Counters are
  DB-backed sliding windows (`api_usage_counters`), no Redis dependency.
- Optional (prod recommends): `AGENT_TASKS_CELERY_EXECUTION=true` on the Vercel
  API env so initial runs are routed through the outbox and execute on the
  Render worker instead of the serverless request thread. Use the Supabase
  **transaction pooler (6543)** URL for the API/worker runtime (session pooler
  5432 caps at 15 client connections → `EMAXCONNSESSION` under concurrency);
  keep 5432 for alembic migrations.

## Guarantees

1. No Vercel function waits on GitHub Actions.
2. Every state transition after PARK is persisted before the next step.
3. Evaluation/reporting execute at most once per task (claim guard).
4. Tasks can never strand: event path + sweep-time recovery converge either
   to COMPLETED or to an explicit FAILED branch.
5. The Plan-Progress Invariant is untouched for genuine reasoning loops;
   parked tasks bypass it entirely because their process has exited.
