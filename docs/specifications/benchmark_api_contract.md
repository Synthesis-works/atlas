# Benchmark API Contract (Phase A)

This document defines the interface for Benchmark Authoring.

## 1. Resource Hierarchy

The API follows a strict RESTful resource hierarchy:

```text
Organizations
    ↓
Projects
    ↓
Benchmarks
    ↓
Benchmark Versions
    ↓
Executions
    ↓
Evaluations
    ↓
Reports
```

## 2. API Endpoints

### Benchmark Management

#### `POST /projects/{project_id}/benchmarks`
Creates a new logical benchmark (starts in `PROPOSAL`).
**Request**:
```json
{
  "name": "Math Reasoning Suite",
  "objective": "Evaluates complex mathematical reasoning",
  "category_ids": ["uuid"],
  "capability_ids": ["uuid"]
}
```
**Response (201 Created)**:
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "state": "PROPOSAL",
  "name": "Math Reasoning Suite"
}
```

#### `GET /projects/{project_id}/benchmarks`
Lists benchmarks in a project.

#### `GET /benchmarks/{benchmark_id}`
Retrieves details of a logical benchmark.

### Benchmark Versioning

#### `POST /benchmarks/{benchmark_id}/versions`
Creates a new editable version (starts in `DRAFT`). Fails if an active editable version already exists.
**Request**:
```json
{
  "version_string": "v1.0.0",
  "dataset_version_ids": ["uuid", "uuid"],
  "evaluation_strategy_id": "uuid"
}
```
**Response (201 Created)**:
```json
{
  "id": "uuid",
  "benchmark_id": "uuid",
  "version_string": "v1.0.0",
  "state": "DRAFT"
}
```

#### `GET /benchmarks/{benchmark_id}/versions`
Lists all versions of a benchmark.

#### `PUT /benchmark-versions/{version_id}`
Updates a `DRAFT` version's configuration.
**Response (200 OK)**

### Lifecycle Actions

#### `POST /benchmark-versions/{version_id}/validate`
Transitions a `DRAFT` to `VALIDATION` and initiates checks.
**Response (202 Accepted)**

#### `POST /benchmark-versions/{version_id}/publish`
Transitions a `REVIEW` version to `PUBLISHED`.
**Response (200 OK)**

#### `POST /benchmark-versions/{version_id}/archive`
Transitions a `PUBLISHED` version to `ARCHIVE`.
**Response (200 OK)**


## 3. Standard Error Codes
- **400 Bad Request**: Invalid input data or validation failure.
- **401 Unauthorized**: Missing or invalid authentication token.
- **403 Forbidden**: Insufficient permissions (e.g., trying to publish without admin rights).
- **404 Not Found**: Resource does not exist.
- **409 Conflict**: State transition violation (e.g., publishing a `PROPOSAL`) or breaking concurrency rules (e.g., creating a second active draft).
- **422 Unprocessable Entity**: Semantic validation errors (e.g., missing dataset binding during validation).
