# Worker Protocol Specification (Phase B)

This document acts as the formal contract between the Atlas backend and any worker attempting to pull, execute, and report on Benchmark Executions.

## 1. Overview
Workers pull work dynamically using an active-polling mechanism over HTTP.
The Backend guarantees at-most-one active worker per execution attempt using a Lease mechanism.

## 2. Lease Acquisition & Heartbeats
- **Lease Duration**: Leases are granted for an initial duration of **300 seconds** (5 minutes).
- **Heartbeat Interval**: Workers MUST send a heartbeat every **60 seconds**.
- **Ownership Invariant**: A lease is valid if and only if `lease.worker_id == request.worker_id` AND `lease.expires_at > now()`.
- **Heartbeat Expiry**: If a heartbeat is missed and the lease duration expires, the backend `Sweeper` (or the next acquisition request) will mark the attempt as `FAILED` (Lease Expired), and if max retries aren't exceeded, it will transition back to `QUEUED` for another worker to pick up.

## 3. Endpoints

All worker interactions occur over internal, authenticated API routes: `/api/v1/internal/workers/*`

### 3.1. Acquire Work
`POST /internal/workers/acquire`
- **Request**:
  ```json
  {
    "worker_id": "uuid",
    "capabilities": ["python", "docker"]
  }
  ```
- **Response**:
  - `200 OK`: A lease was acquired. Returns an `AcquireResponse` (or `LeaseGrant`):
    ```json
    {
      "lease_id": "uuid",
      "execution_id": "uuid",
      "attempt_id": "uuid",
      "heartbeat_interval_seconds": 60,
      "lease_duration_seconds": 300,
      "benchmark_version_id": "uuid"
    }
    ```
  - `204 No Content`: No schedulable work available.

### 3.2. Heartbeat
`POST /internal/executions/{execution_id}/heartbeat`
- **Request**:
  ```json
  {
    "worker_id": "uuid"
  }
  ```
- **Response**:
  - `200 OK`: Lease successfully extended by 300 seconds.
  - `409 Conflict`: The execution is no longer in `RUNNING`/`STARTING` state (e.g. cancelled by user).
  - `403 Forbidden`: `LeaseOwnershipError` (this worker does not own the active lease).

### 3.3. Complete Work
`POST /internal/executions/{execution_id}/complete`
- **Request**:
  ```json
  {
    "worker_id": "uuid",
    "status": "SUCCESS", // or FAILED
    "error_message": "Optional error context if FAILED",
    "artifacts": [
      {
        "type": "LOGS",
        "storage_uri": "s3://path/to/logs"
      }
    ]
  }
  ```
- **Response**:
  - `200 OK`: Completion accepted.
  - `409 Conflict`: Duplicate completion (Execution already terminal). The backend should enforce idempotency here. If the worker resends exactly the same completion, it can be 200 OK. If a *different* worker attempts completion, it throws a `LeaseOwnershipError` (403).

## 4. Error Handling (Worker side)
- **403 on Heartbeat/Complete**: The worker MUST immediately cease execution and terminate the local sandbox. It has lost the lease.
- **409 on Heartbeat**: The worker MUST immediately cease execution. The execution was likely cancelled.
- **5xx Errors**: The worker MUST retry with exponential backoff.

## 5. Idempotency and Duplicates
- **Duplicate Heartbeat**: Safe. Simply pushes the expiration window forward by 300 seconds from `now`.
- **Duplicate Completion**: If the same worker sends `SUCCESS` multiple times for the same execution, the application service will check if `status == COMPLETED` and silently return 200 OK.

## 6. Worker Shutdown
When a worker gracefully shuts down, it SHOULD attempt to fail its current execution, releasing it back to the queue immediately rather than waiting 5 minutes for the lease to expire.
