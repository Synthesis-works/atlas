# Execution API Contract (Phase B)

This document defines the interface for the Execution control-plane API.
Authorization rules are strictly enforced per operation.

## 1. Resource Hierarchy

```text
Benchmarks
    ↓
Benchmark Versions
    ↓
Executions (Control Plane)
```

## 2. API Endpoints

### `POST /benchmarks/{benchmark_version_id}/executions`
Creates and queues a new execution for a specific benchmark version.

**Authorization**:
- Subject must possess `benchmark:execute` permission.
- Subject must have access to the Project containing the benchmark.

**Request**:
Empty body (configuration options may be added later).

**Response (201 Created)**:
```json
{
  "id": "uuid",
  "benchmark_version_id": "uuid",
  "status": "QUEUED",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "created_by": "uuid",
  "max_retries": 3,
  "attempts": []
}
```

### `GET /executions/{execution_id}`
Retrieves details of an execution including attempts, leases, and artifacts.

**Authorization**:
- Subject must possess `execution:read` permission.
- Visibility is constrained to executions created by the user, UNLESS the user possesses `project:admin` or `execution:read_all` to view any execution within their project.

**Response (200 OK)**

### `GET /executions`
Lists executions.

**Authorization**:
- Subject must possess `execution:read` permission.
- Returns only executions created by the caller, UNLESS caller has project-level visibility.

**Query Parameters**:
- `limit`: int (default 20, max 100)
- `offset`: int (default 0)
- `benchmark_version_id`: Optional[uuid]
- `status`: Optional[str]

**Response (200 OK)**
```json
{
  "items": [],
  "total": 0
}
```

### `POST /executions/{execution_id}/cancel`
Cancels a running or queued execution.

**Authorization**:
- Subject must possess `execution:cancel` permission.
- A user can ONLY cancel their own execution, UNLESS they possess `project:admin` permission to cancel others' executions.

**Response (200 OK)**

## 3. Standard Error Codes
- **400 Bad Request**: General domain validation error.
- **401 Unauthorized**: Missing or invalid authentication token.
- **403 Forbidden**: Insufficient permissions, or attempting to read/cancel an execution owned by someone else without project admin rights.
- **404 Not Found**: Execution does not exist (or is hidden from user).
- **409 Conflict**: Invalid state transition (e.g., cancelling an already completed execution).
