# ADR-002: Observability Architecture

## Context
As the Atlas platform transitions into Phase C, it needs to be operable, debuggable, and monitorable in production. We need to introduce logging, metrics, and tracing without polluting the core domain logic (which we rigorously protected in Phase B). Furthermore, we want to ensure vendor neutrality.

## Decisions

### 1. Structured Logging (JSON) over Plain Text
**Decision:** All application logs will be emitted as structured JSON objects containing standard fields (`timestamp`, `level`, `category`, `correlation_id`, `trace_id`, `span_id`) and specific event payloads.
**Reasoning:** 
- In distributed environments, plain text logs require complex regex parsing (e.g., Grok) to extract data. 
- JSON logging allows log aggregators (like ELK, Datadog) to instantly index attributes. This makes querying for "all logs where category = EXECUTION and status = FAILED" trivial.
- We will use `structlog` to enforce this structure across the Python backend.

### 2. ContextVars for Correlation IDs
**Decision:** We will inject a `correlation_id` (and `trace_id`) at the HTTP Router layer (via Middleware) falling back to a `UUIDv7` if missing, and propagate it implicitly using Python's `contextvars`.
**Reasoning:** 
- Passing `correlation_id` explicitly through every function signature (from Router -> App -> Domain -> Repo) would severely pollute the domain model and break encapsulation.
- `contextvars` provides thread-safe/async-safe context local storage, allowing the logging processor to grab the ID automatically when `logger.info()` is called anywhere in the stack.

### 3. Separate Metrics from Domain Logic via TelemetrySink
**Decision:** The Domain layer will not contain any metrics libraries or counters. It will only emit Domain Events (e.g., `ExecutionCompletedEvent`). The Event Publisher will route these events to an abstract `TelemetrySink` rather than a direct Prometheus client.
**Reasoning:** 
- If the domain aggregates incremented Prometheus counters directly, they would become tightly coupled to the observability infrastructure.
- The `TelemetrySink` abstraction allows us to hot-swap or dual-publish to Prometheus, OpenTelemetry, or Null sinks without changing application/domain logic.

### 4. Separate Liveness and Readiness Probes
**Decision:** The system will expose `/health/live` and `/health/ready` rather than a unified `/health` endpoint.
**Reasoning:** 
- Kubernetes requires distinguishing between "the process is running" (Liveness) and "the process can serve traffic because dependencies are connected" (Readiness).

## Consequences
- **Positive:** Debugging production issues will be heavily simplified due to the `correlation_id` tying together all logs for a specific request.
- **Positive:** Our domain aggregates remain completely agnostic to how they are monitored.
- **Positive:** We are protected against Prometheus vendor lock-in.
- **Negative:** Developers must remember to use the structured logger instead of standard `print()` or the default `logging` module to ensure fields are injected.
