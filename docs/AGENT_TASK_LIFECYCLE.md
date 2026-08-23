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
    │  run_benchmark returns DISPATCHED (execution_backend == github_actions)
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
```

Synchronous/local backends (`docker`, local dev) do not park: the PR #54
inline `wait_for_runs` phase remains active and the invariant exemption for
sanctioned waiting polls still applies there.

## Components

| Concern | Implementation |
|---|---|
| Persisted continuation state | `agent_task_records.snapshot` (full `AgentTask.model_dump`) — plan, observations, trace, execution_ids, counters. Loader: `AgentTask.model_validate(snapshot)`. New fields: `waiting_since`, `resume_count`. |
| Park transition | `AtlasAgent.run_task` loop, post-`run_benchmark` DISPATCHED hook (`apps/backend/agent/agent.py`), gated on `settings.execution_backend == "github_actions"`; traces `AGENT_TASK_WAITING`. |
| Resume trigger | `AgentTaskResumeSubscriber` registered in `outbox_sweep_task`'s `CompositeEventPublisher` (`apps/backend/worker/tasks.py`). Enqueue-only; no DB work in the subscriber. |
| Resume executor | `resume_agent_task` Celery task + `resume_agent_task_core` / `handle_terminal_execution_event` / `recover_stale_waiting_tasks` in `apps/backend/worker/agent_resume.py`, running on the Render worker (eager inline Celery; no broker required). |
| Idempotency | Conditional claim `status == 'WAITING_FOR_EXECUTION'` flips to `RESUMED` exactly once per task. Duplicate completion events, outbox redeliveries, and racing sweeps no-op via `NOT_CLAIMED`. |
| Multi-execution gating | A task resumes only when ALL tracked executions are terminal; authoritative outcome is read from the `executions` table, never trusted from the event payload. Partial-failure tasks stay WAITING until the last run settles. |
| Lost-event safety net | `recover_stale_waiting_tasks` runs inside every outbox sweep: all-terminal WAITING rows are resumed (event raced ahead of persist or was lost); non-terminal rows past `AGENT_STALE_WAITING_MINUTES`/wait deadline are force-failed `AGENT_RESUME_TIMEOUT`; crashed `RESUMED` rows older than 10 min are re-claimed up to `MAX_RESUME_ATTEMPTS = 3`, then failed `AGENT_RESUME_FAILED`. |

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

## Deployment prerequisites

- Render `atlas-worker` env must include the reasoning provider keys used by
  resumed runs (at minimum `GEMINI_API_KEY`; add fallback provider keys as
  configured). Without them resume fails with provider errors and the task
  ends `FAILED` after retries.
- Optional tuning: `AGENT_STALE_WAITING_MINUTES` (default 15),
  `AGENT_EXECUTION_WAIT_DEADLINE_SECONDS` (default 480, unchanged).

## Guarantees

1. No Vercel function waits on GitHub Actions.
2. Every state transition after PARK is persisted before the next step.
3. Evaluation/reporting execute at most once per task (claim guard).
4. Tasks can never strand: event path + sweep-time recovery converge either
   to COMPLETED or to an explicit FAILED branch.
5. The Plan-Progress Invariant is untouched for genuine reasoning loops;
   parked tasks bypass it entirely because their process has exited.
