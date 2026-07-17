# Execution API Contract

This document defines the black-box contract that the Execution Service provides to all downstream consumers (e.g. Evaluation, Reporting). Downstream services must depend on this contract, not internal implementation details.

## Commands
The following Commands are the **only** write entry-points to the Execution Engine. No direct database mutations are permitted.

* `CreateRunCommand`: Instructs the engine to provision a new Run.
* `ValidateRunCommand`: Triggers validation checks before scheduling.
* `CancelRunCommand`: Instructs the engine to transition the run into an `ABORTING` state, halting new task scheduling.
* `ResumeRunCommand`: Resumes a `PAUSED` run back into the `QUEUED` state.
* `RetryRunCommand`: (Future) Triggers a manual retry mechanism.
* `RegisterWorkerCommand`: Onboards a new Worker Node into the pool.
* `ClaimTasksCommand`: Exclusively atomically allocates tasks to a Worker.

## Events
Consumers must listen to these events (append-only) to derive state.

* `RUN_CREATED`
* `RUN_VALIDATED`
* `RUN_CANCELLED`
* `RUN_COMPLETED`
* `RUN_FAILED`
* `TASK_ASSIGNED`
* `TASK_COMPLETED`
* `TASK_FAILED`
* `TASK_REQUEUED`
* `RECOVERY_SKIPPED`
* `WORKER_LOST`

## Models
Entities exposed by the Execution API:

* `AtlasRun`: The top-level execution entity. Terminal states are `COMPLETED`, `FAILED`, and `CANCELLED`.
* `AtlasTask`: A single unit of execution bound to a Run. Terminal states are `COMPLETED` and `FAILED`.
* `ExecutionWorker`: The compute node definition and status (`READY`, `BUSY`, `UNHEALTHY`, `OFFLINE`).

## Guarantees
The Execution Service firmly provides these guarantees to all consumers:

1. **Atomic Claiming**: A single Task can only be successfully claimed by exactly one Worker at any given moment.
2. **Exclusive Ownership**: A Worker cannot complete or fail a task that is leased to another Worker.
3. **Event Ordering**: Events are strictly chronologically ordered and append-only.
4. **Recovery Ownership**: Execution intrinsically owns its own failure handling. Downstream consumers will simply see `TASK_REQUEUED` or `TASK_FAILED` without needing to invoke recovery mechanisms themselves.
