# Execution Events

To ensure loose coupling, the Execution engine will publish structured Domain Events when critical state changes occur. Other bounded contexts (like Notifications, Reporting, or Billing) can subscribe to these events without tightly integrating with the Execution database.

All events inherit from the base `DomainEvent` class established in Phase A.

## Event Definitions

### `ExecutionQueuedEvent`
- **Triggered when**: A user successfully submits an execution request.
- **Payload**:
  - `execution_id`: UUID
  - `benchmark_version_id`: UUID
  - `submitted_by`: UUID
  - `timestamp`: UTC DateTime

### `ExecutionStartedEvent`
- **Triggered when**: A worker acquires a lease and transitions the execution to `STARTING` or `RUNNING`.
- **Payload**:
  - `execution_id`: UUID
  - `attempt_id`: UUID
  - `worker_id`: UUID
  - `timestamp`: UTC DateTime

### `WorkerLeaseExpiredEvent`
- **Triggered when**: The background Sweeper detects a lease has passed its `expires_at` threshold and reclaims the execution.
- **Payload**:
  - `execution_id`: UUID
  - `attempt_id`: UUID
  - `worker_id`: UUID (The worker that dropped the lease)
  - `timestamp`: UTC DateTime

### `ExecutionCompletedEvent`
- **Triggered when**: An execution successfully finishes and all artifacts are saved.
- **Payload**:
  - `execution_id`: UUID
  - `attempt_id`: UUID
  - `artifact_ids`: List[UUID]
  - `timestamp`: UTC DateTime

### `ExecutionFailedEvent`
- **Triggered when**: An execution fails, either permanently or prior to a retry.
- **Payload**:
  - `execution_id`: UUID
  - `attempt_id`: UUID
  - `error_message`: String
  - `will_retry`: Boolean (True if `attempts < MAX_RETRIES`)
  - `timestamp`: UTC DateTime
