# Execution API Contract

This document outlines the REST API for Phase B. Crucially, the public Control Plane (where users trigger runs) is strictly separated from the internal Data Plane (where worker nodes acquire leases and report progress).

## Control Plane (Public API)

Prefix: `/api/v1`
Authentication: Standard User Bearer Token (Project Role Based)

### `POST /benchmarks/{benchmark_id}/executions`
Submits a new execution for a published benchmark version.
- **Request Body**:
  ```json
  {
    "benchmark_version_id": "uuid"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "id": "uuid",
    "status": "QUEUED"
  }
  ```

### `GET /executions/{execution_id}`
Retrieves the status and history of an execution.
- **Response**: `200 OK`
  ```json
  {
    "id": "uuid",
    "status": "RUNNING",
    "attempts": [
       {"id": "uuid", "status": "FAILED", "started_at": "...", "finished_at": "..."}
    ],
    "artifacts": []
  }
  ```

### `POST /executions/{execution_id}/cancel`
Requests cancellation of an ongoing or queued execution.
- **Response**: `202 Accepted`

---

## Data Plane (Internal Worker API)

Prefix: `/internal/workers`
Authentication: Mutual TLS (mTLS), VPC routing, or strict internal Service Account token. (Do NOT expose publicly).

### `POST /internal/workers/acquire`
Called by a polling worker to acquire a lease on the next available `QUEUED` execution.
- **Request Body**:
  ```json
  {
    "worker_id": "uuid",
    "capabilities": ["gpu", "high-mem"]
  }
  ```
- **Response**: `200 OK` (Execution locked) or `204 No Content` (Queue empty)
  ```json
  {
    "execution_id": "uuid",
    "lease_id": "uuid",
    "expires_at": "timestamp"
  }
  ```

### `POST /internal/executions/{execution_id}/heartbeat`
Called periodically (e.g. every 30s) by the worker to extend the lease.
- **Request Body**:
  ```json
  {
    "lease_id": "uuid",
    "status": "RUNNING"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "action": "CONTINUE" // Or "CANCEL" if user requested cancellation
  }
  ```

### `POST /internal/executions/{execution_id}/complete`
Called when the worker finishes (success or failure).
- **Request Body**:
  ```json
  {
    "lease_id": "uuid",
    "status": "COMPLETED", // or FAILED
    "error_message": null,
    "artifacts": [
       {"type": "MODEL_OUTPUT", "storage_uri": "s3://..."}
    ]
  }
  ```
- **Response**: `200 OK`
