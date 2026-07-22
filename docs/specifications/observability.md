# Observability Specification (Phase C.1)

This specification defines the observability layer for the Atlas backend, designed to make the platform self-explaining, observable, and easy to operate without compromising domain purity.

## 1. Structured Logging

All significant actions must emit structured JSON logs. The log schema guarantees consistency across all bounded contexts.

### Base Log Schema
Every log entry must contain the following baseline fields:
- `timestamp`: ISO-8601 UTC timestamp
- `level`: Log level (INFO, WARNING, ERROR, etc.)
- `category`: Log category (e.g., `EXECUTION`, `WORKER`, `DATABASE`, `HTTP`, `AUTH`, `SCHEDULER`, `EVALUATION`)
- `correlation_id`: A unique trace ID spanning the entire request lifecycle
- `trace_id`: Initially identical to `correlation_id`, prepared for OpenTelemetry integration
- `span_id`: Unique identifier for the current operation span
- `message`: Human-readable description
- `event`: (Optional) The specific domain event name being logged (e.g., `ExecutionCompleted`)

### Logging Categories
To make searching logs dramatically easier, every log must fall into a predefined category. Examples:
- `HTTP`: API requests and responses
- `AUTH`: Authentication and Authorization checks
- `DATABASE`: Queries, connection pooling, migrations
- `EXECUTION`: Benchmark orchestration lifecycle
- `WORKER`: Worker lease acquisition and heartbeats
- `SCHEDULER`: Background sweeps and cron tasks
- `EVALUATION`: Judging and metric calculation pipelines

### Domain-Specific Payloads
When a domain event occurs, the log must include a payload object.

**Execution Created**
```json
{
  "category": "EXECUTION",
  "event": "ExecutionCreated",
  "payload": {
    "execution_id": "uuid",
    "benchmark_id": "uuid",
    "user_id": "uuid",
    "version": 1
  }
}
```

## 2. Redaction Policy

To maintain security and privacy, the observability layer must adhere to strict redaction rules.

**NEVER Log:**
- Tokens (JWTs, session tokens)
- Passwords or hashes
- Secrets or API keys
- Credentials of any kind
- Prompt contents (if sensitive or customer-owned)

**ALLOWED to Log:**
- Resource IDs (Execution IDs, Benchmark IDs, Worker IDs)
- Timestamps and durations
- HTTP status codes
- Non-sensitive metadata (e.g., attempt counts, artifact counts)

## 3. Correlation & Trace IDs

### ID Resolution Fallback Logic
1. **Incoming HTTP Request**: Middleware checks for the `X-Correlation-ID` header.
2. **Present?**: YES -> Use the provided ID (trusting the upstream API gateway).
3. **Absent?**: NO -> Generate a new `UUIDv7` (time-ordered).
4. **Context Propagation**: Store the resolved ID in a Python `contextvar`.
5. **Reuse**: Propagate implicitly and attach to all subsequent logs, events, and outgoing requests.

*Note: `trace_id` will equal `correlation_id` initially, until a full OpenTelemetry agent supersedes it.*

## 4. Metrics

Metrics provide aggregated telemetry. To remain vendor-neutral, metrics are routed through an abstract `TelemetrySink`, completely decoupled from the domain.

### Naming Convention
All metrics must follow the `atlas_` prefix and clearly describe the measurement.

### Counters (Cumulative)
- `atlas_execution_created_total`
- `atlas_execution_completed_total`
- `atlas_execution_failed_total`
- `atlas_leases_expired_total`
- `atlas_worker_acquire_success_total`
- `atlas_worker_acquire_failure_total`

### Histograms (Distributions)
- `atlas_execution_duration_seconds` (Time from QUEUED to COMPLETED/FAILED)
- `atlas_heartbeat_latency_seconds` (Time delta between heartbeats)
- `atlas_scheduler_cycle_seconds` (Time taken by the sweeper loop)
- `atlas_worker_completion_time_seconds` (Time taken by worker to run benchmark)

### Gauges (Point-in-time)
- `atlas_active_workers` (Derived from active leases)
- `atlas_queued_executions` (Executions in QUEUED state)
- `atlas_running_executions` (Executions in STARTING or RUNNING state)

## 5. Event Versioning

As the system evolves, event schemas will change. The EventPublisher will enforce event versioning to prevent breaking downstream consumers (like the Outbox or external reporting systems).
Every emitted event will carry a `version` attribute, starting at `1`.

## 6. Log Levels & Sampling Strategy

We strictly define when to use which log level to prevent alert fatigue:
- `DEBUG`: Verbose information useful for development (e.g., `Repository Query executed`). Subject to **configurable sampling** (e.g., only sample 1% in production) to prevent log volume explosions.
- `INFO`: Normal business events and domain state transitions (e.g., `ExecutionCreated`). Sampled at 100%.
- `WARNING`: Recoverable anomalies that do not fail the request (e.g., `Lease Expired`).
- `ERROR`: Operations that fail or hit limits but don't crash the system (e.g., `Execution Failed`).
- `CRITICAL`: System-level failures requiring immediate intervention (e.g., `Database unavailable`).

## 7. Logical Dashboard Plan

While we are not building Grafana immediately, metrics are designed to feed into the following logical dashboards:
- **API Dashboard**: Throughput, latencies (p95/p99), and 4xx/5xx error rates.
- **Execution Dashboard**: Queue depth, end-to-end durations, failure rates.
- **Worker Dashboard**: Active workers, heartbeat latencies, starvation metrics.
- **Scheduler Dashboard**: Cycle times, lease expiration counts, concurrency locks.
- **Database Dashboard**: Connection pool saturation, query durations.
