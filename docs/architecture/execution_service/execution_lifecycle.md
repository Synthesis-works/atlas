# Execution Lifecycle

The Execution Service manages the entire lifecycle of an `AtlasRun`. When an external caller (Evaluation Service) requests a run, the following lifecycle executes:

1. **Initialization:**
   - Database records for the `AtlasRun` and its component `AtlasTask`s are created in the `CREATED` state.

2. **Validation (`VALIDATING`):**
   - The Execution Controller verifies that the benchmark, adapter, target model, and datasets exist.
   - It checks user permissions, quotas, and configuration validity.
   - If validation fails, the run transitions to `FAILED`. Otherwise, it transitions to `QUEUED`.

3. **Scheduling & Dispatch (`QUEUED`):**
   - The **Scheduler** evaluates the queued run against concurrency limits, priorities, and fairness rules.
   - When conditions are met, the Scheduler pushes tasks to the Dispatch Queue.
   - The chosen Adapter (e.g., K8s) allocates resources (e.g., spins up a Pod). State transitions to `STARTING`.

4. **Execution (`RUNNING`):**
   - The Worker environment initializes and claims the Run.
   - The Worker begins processing individual `AtlasTask`s.
   - State transitions to `RUNNING`.
   - The Worker sends periodic heartbeats to the Execution Service API to confirm it is alive.
   - Task progress, raw outputs, and logs are incrementally flushed to the API.

5. **Finalization (`COMPLETED` or `FAILED`):**
   - Upon completing all tasks (or upon a terminal failure), the Worker uploads any final artifacts to Object Storage.
   - The Worker notifies the API of completion.
   - The Execution Service aggregates task results, records the completion timestamp, and transitions the Run to `COMPLETED`.

6. **Handoff:**
   - The Execution Service emits a completion event (via Webhook, Server-Sent Events, or PubSub).
   - The Evaluation Service picks up the `COMPLETED` Run to begin scoring.

## Fault Tolerance & Recovery Lifecycle

### Stale Workers (Crash Detection)
- The **Watchdog Daemon** runs periodically, looking for active tasks whose `last_heartbeat_at` exceeds the threshold.
- If a stale worker is detected, the daemon marks the active task as `FAILED` (Reason: `HEARTBEAT_TIMEOUT`).

### Retry Mechanisms
- Tasks support a `max_retries` configuration.
- If a task fails, the **Scheduler** checks the `retry_count`.
- If `retry_count < max_retries`, the task state is reset to `QUEUED`, `retry_count` is incremented, and it is re-dispatched.
- If retries are exhausted, the task is marked `FAILED`. Depending on the Run's `fail_fast` policy, the entire Run may transition to `FAILED`.
