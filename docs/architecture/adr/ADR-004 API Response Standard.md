# ADR-004: API Response Standard

**Status:** Accepted

## Context
As the Atlas Backend API scales and encompasses multiple domains (Execution, Evaluation, Reporting, Datasets), maintaining consistency across endpoints becomes challenging. Without a standard envelope, clients must write custom parsing and error-handling logic for each endpoint, increasing integration friction and the potential for bugs.

## Decision
We will enforce a unified JSON response envelope for all API endpoints.

**Success Envelope:**
```json
{
  "success": true,
  "message": "Optional human-readable message",
  "data": { ... },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  }
}
```

**Error Envelope:**
```json
{
  "success": false,
  "error": {
    "code": "APPLICATION_SPECIFIC_CODE",
    "message": "Human-readable error description",
    "details": { ... } // Optional context/validation errors
  },
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  }
}
```

## Consequences
- **Positive:** Uniform client integration. Global middleware and exception handlers can intercept and format all responses seamlessly.
- **Positive:** Traceability is built-in (`request_id` and `timestamp` are guaranteed in every response).
- **Negative:** Slightly increased overhead/verbosity compared to returning raw resources (e.g. `[1, 2, 3]`).

## Alternatives Considered
- Returning raw resources (e.g. HTTP 200 with raw JSON objects/arrays). Rejected because it lacks consistent metadata and forces error data to be handled separately.
- JSON:API specification. Rejected because it is overly complex for our current needs and introduces unnecessary indirection for simple domain models.
