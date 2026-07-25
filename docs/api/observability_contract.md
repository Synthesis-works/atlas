# Observability API Contract

This document defines the system-level endpoints exposed by the Atlas backend to support observability (health checks, liveness probes, and metrics scraping).

## 1. System Health

The health endpoints are split to properly support Kubernetes lifecycle management.

### Liveness Probe
**Endpoint:** `GET /health/live` or `GET /api/v1/system/health/live`

**Purpose:** Verifies the process is running. If this fails, the orchestrator should restart the pod.

**Response (200 OK):**
```json
{
  "status": "alive",
  "version": "0.9.0",
  "timestamp": "2026-07-20T10:00:00Z"
}
```

### Readiness Probe
**Endpoint:** `GET /health/ready` or `GET /api/v1/system/health/ready`

**Purpose:** Verifies the application is ready to receive traffic (i.e., database and storage connections are active). If this fails, the orchestrator should temporarily remove the pod from the load balancer rotation.

**Response (200 OK):**
```json
{
  "status": "ready",
  "checks": {
    "database": "connected",
    "storage": "connected"
  },
  "timestamp": "2026-07-20T10:00:00Z"
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "checks": {
    "database": "disconnected",
    "storage": "connected"
  },
  "timestamp": "2026-07-20T10:00:00Z"
}
```

## 2. Metrics Scraping

**Endpoint:** `GET /metrics` or `GET /api/v1/system/metrics`

**Purpose:** Exposes aggregated application metrics in Prometheus plaintext format for scraping by a Prometheus server or OTEL collector. Driven internally by the `TelemetrySink`.

**Response (200 OK):**
*(Text / Plain format)*
```text
# HELP atlas_execution_created_total Total number of benchmark executions created
# TYPE atlas_execution_created_total counter
atlas_execution_created_total 154

# HELP atlas_execution_duration_seconds Time taken from queued to terminal state
# TYPE atlas_execution_duration_seconds histogram
atlas_execution_duration_seconds_bucket{le="10.0"} 45
atlas_execution_duration_seconds_bucket{le="30.0"} 120
atlas_execution_duration_seconds_bucket{le="+Inf"} 154
atlas_execution_duration_seconds_sum 3540.5
atlas_execution_duration_seconds_count 154

# HELP atlas_active_leases Number of currently active execution leases
# TYPE atlas_active_leases gauge
atlas_active_leases 5
```

## 3. Telemetry Headers

The API enforces and respects specific headers for tracing and correlation across service boundaries.

**Incoming Headers (Parsed by Middleware):**
- `X-Correlation-ID`: If provided by the client (e.g., an API Gateway), the backend uses this ID for log correlation. If absent, the backend generates a new `UUIDv7` (time-ordered).
- `X-Trace-ID`: Standard tracing header (W3C or B3 context). If absent, defaults to `X-Correlation-ID` initially until OTEL propagates it fully.

**Outgoing Headers (Appended to Response):**
- `X-Correlation-ID`: The ID used to trace this specific request, returned to the client to assist in support and debugging.
