# Execution Service Invariants

This document establishes the fundamental guarantees of the Execution Service.
These rules form the "constitution" of the architecture. Whenever changing code, you must verify you haven't broken any of these invariants.

## State Machine & Lifecycles
* A Run can never transition `COMPLETED` → `RUNNING`.
* A Task belongs to exactly one Run.
* Evaluation only consumes `COMPLETED` runs.

## Data & Event Integrity
* Every state transition MUST create a `RunEvent` in the same database transaction.
* `RunEvent` records are immutable once written.
* Artifacts (outputs, logs) are immutable once uploaded.
* `RunEvent` payload must always include `event_type`, `run_id`, and `timestamp`, with `task_id` and `worker_id` populated where applicable.
* Events should always be generated in chronological order of operations (e.g. `TASK_CLAIMED` -> `TASK_STARTED` -> `TASK_COMPLETED`).

## Separation of Concerns (Controller, Scheduler, Worker)
* Workers NEVER modify Run or Task state directly in the database. They must communicate purely via commands (sending facts like `TaskCompleted`, `Heartbeat`).
* Only the Execution Controller changes lifecycle states and writes events.
* The Scheduler NEVER decides retries. Retries are strictly owned by the Execution Controller.
* The Scheduler is purely responsible for answering: "Which worker should run this task, and when?"

## Task Ownership and Concurrency
* A Worker may only complete or fail tasks that it currently owns.
* Task ownership is exclusive. A task can only transition from `QUEUED` to `RUNNING` once.
* Only the Execution Controller may transfer ownership. Atomic claiming prevents race conditions.
