# Execution Failure Model

Execution systems are predominantly about managing failure and concurrency. This document explicitly defines the failure semantics for the Atlas Execution Engine.

## Worker Crash & Orphaned Executions
- **Scenario**: A worker acquires a lease, begins execution, and suddenly terminates (OOM, network loss, hard crash) before sending a completion or failure signal.
- **Policy**: The `ExecutionLease` maintains an `expires_at` timestamp. A background system (Sweeper) will periodically scan for leases where `expires_at < NOW()`.
- **Action**: When a lease expires, the Sweeper transitions the Execution to `RETRYING` (if under max retries) or `FAILED`, and deletes the lease.

## Retry Policy & Exponential Backoff
- **Scenario**: An execution fails due to a transient error (e.g., API rate limit downloading a dataset) or lease expiration.
- **Policy**: Executions will automatically retry up to `MAX_RETRIES` (default: 3).
- **Action**: 
  - On failure, attempt count is incremented.
  - If `attempts < MAX_RETRIES`, transition to `RETRYING`.
  - The execution is placed back into the `QUEUED` state after a backoff period. (Future iteration may introduce an explicit backoff delay; initially it can be immediately re-queued).

## Duplicate Completion (Idempotency)
- **Scenario**: A worker sends a `COMPLETED` payload, the database commits, but the network drops the HTTP 200 OK. The worker retries the `POST /complete` request.
- **Policy**: The Data Plane API must be idempotent. 
- **Action**: If a worker attempts to complete an execution that is already `EVALUATING` or `COMPLETED`, the server must return `200 OK` (or `409 Conflict` if the payload payload materially differs) and take no further action.

## Heartbeat Timeouts & Misses
- **Scenario**: A worker is heavily utilizing CPU and fails to send a heartbeat in time, but is still running. The Sweeper re-queues the execution.
- **Policy**: A worker whose lease is expired is no longer the owner.
- **Action**: When the slow worker finally sends a heartbeat, the server will detect the `lease_id` is invalid or the execution is owned by another lease. The server responds with `action=CANCEL` (or `403 Forbidden`). The worker is obligated to immediately terminate its process.

## Artifact Upload Failure
- **Scenario**: The execution completes successfully locally, but the worker fails to upload the resulting artifacts to blob storage.
- **Policy**: An execution attempt is not `COMPLETED` unless all outputs are safely persisted.
- **Action**: The worker must report a `FAILED` status with the error `ARTIFACT_UPLOAD_FAILURE`. The execution will be retried (re-run entirely).
