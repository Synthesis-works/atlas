# Reporting API

## Core Endpoints

### Dashboards and Summaries
- `GET /dashboard` - Retrieve high-level project dashboard data.
- `GET /summary` - Retrieve system or project summaries.

### Leaderboards
- `GET /leaderboards`
  - Query parameters: `strategy` (e.g., `overall`, `capability`, `benchmark`), `limit`, `offset`.

### Models
- `GET /models/{id}` - Get reporting details for a specific model.

### Benchmarks
- `GET /benchmarks/{id}` - Get performance reporting for a specific benchmark.

### Capabilities
- `GET /capabilities/{model}` - Retrieve the capability dashboard/profile for a given model.

### Evaluations & Runs
- `GET /evaluations/{id}` - Get detailed evaluation report.
- `GET /runs/{id}` - Get run report details.

### History & Trends
- `GET /history` - Get historical run data.
- `GET /trends` (or similar) - Trend analysis over time.

### Metrics & Reports
- `GET /metrics` - Retrieve aggregate metrics.
- `GET /reports/{id}` - Retrieve a specific saved report.

### Operational Endpoints
- `GET /health` - Health check.
- `GET /versions` - Get API version and component versions.

### Exports
- Exports can be handled via query parameters or specific endpoints (e.g., `GET /reports/{id}/export?format=csv`).
