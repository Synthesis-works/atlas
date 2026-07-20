# Execution Service API

The Execution Service exposes two categories of APIs: External (used by the Evaluation Service and CLI) and Internal (used by execution workers/adapters).

## External API (Control Plane)

These endpoints are used to orchestrate runs from the outside.

### `GET /api/v1/executions/runs`
List and filter execution runs (useful for dashboards and polling).
- **Query Params:** `status`, `project_id`, `benchmark_id`, `model`, `start_date`, `end_date`, `limit`, `offset`
- **Response:** Paginated list of `Run` summaries.

### `POST /api/v1/executions/runs`
Create a new execution run.
- **Payload:** `session_id`, `benchmark_version_id`, `adapter_version_id`, `target_model`, `config` (fail_fast, retries, etc.)
- **Response:** `201 Created` with `run_id`. State is initialized to `CREATED`.

### `GET /api/v1/executions/runs/{run_id}`
Get the current status and metadata of a specific run.
- **Response:** `Run` object including current `status`, `started_at`, `completed_at`, and progress metrics.

### `GET /api/v1/executions/runs/{run_id}/events`
Stream lifecycle events for a run (e.g., Server-Sent Events or WebSockets).
- **Response:** Real-time stream of state changes, task completions, and log snippets.

### `POST /api/v1/executions/runs/{run_id}/cancel`
Send a cancel signal to an active run.
- **Response:** `202 Accepted` (transitioning to `CANCELLED`).

### `POST /api/v1/executions/runs/{run_id}/pause`
Pause an active run.
- **Response:** `202 Accepted` (transitioning to `PAUSED`).

### `POST /api/v1/executions/runs/{run_id}/resume`
Resume a paused run.
- **Response:** `202 Accepted` (transitioning back to `VALIDATING` or `QUEUED`).

### `GET /api/v1/executions/runs/{run_id}/outputs`
Fetch the completed outputs and artifacts of a run. Used by Evaluation Service.
- **Response:** Paginated list of tasks, outputs, and artifact URIs.

---

## Internal API (Data Plane)

These endpoints are strictly for the Execution Workers to interact with the Execution API.

### `POST /api/v1/internal/workers/heartbeat`
Workers ping this endpoint periodically to signal they are alive.
- **Payload:** `worker_id`, `run_id`, `active_task_ids[]`

### `GET /api/v1/internal/runs/{run_id}/tasks/claim`
Worker pulls the next batch of tasks to execute from the queue.
- **Payload:** `batch_size`
- **Response:** List of `AtlasTask` objects. Transitions tasks to `RUNNING`.

### `POST /api/v1/internal/tasks/{task_id}/complete`
Worker reports a task as successfully completed.
- **Payload:** `raw_output`, `duration_ms`, `tokens_used`, `artifact_uris[]`
- **Response:** `200 OK`. Transitions task to `COMPLETED`.

### `POST /api/v1/internal/tasks/{task_id}/fail`
Worker reports a task failure.
- **Payload:** `error_message`, `traceback`, `is_fatal`
- **Response:** `200 OK`. Transitions task to `FAILED` (or prompts Scheduler for retry).

### `POST /api/v1/internal/runs/{run_id}/artifacts`
Upload an artifact (e.g., worker logs) directly to the Execution Service.
- **Payload:** Multipart file upload.
- **Response:** `Artifact` metadata including `uri`.
