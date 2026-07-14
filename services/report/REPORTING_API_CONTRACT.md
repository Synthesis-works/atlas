# Reporting API Contract

## Overview
This document specifies the exact API contract for the `v0.7-reporting-core` release. The Reporting Service provides a read-only aggregation layer over Atlas runs and evaluations.

## Base URL
`/api/v1`

## Endpoints

### 1. Dashboards & Summaries
- `GET /dashboard`
  - Returns a high-level project dashboard.
- `GET /summary`
  - Returns a system or project summary.

### 2. Capabilities
- `GET /capabilities/{model_identifier}`
  - **Response (CapabilityDashboardDTO):**
    ```json
    {
      "model_identifier": "string",
      "overall_score": 0.0,
      "scores": [
        {
          "capability_name": "string",
          "score": 0.0
        }
      ]
    }
    ```

### 3. Leaderboards
- `GET /leaderboards`
  - **Parameters:** `strategy` (default: "overall"), `limit` (default: 10)
  - **Response (LeaderboardResponseDTO):**
    ```json
    {
      "strategy": "string",
      "entries": [
        {
          "rank": 1,
          "model_identifier": "string",
          "score": 0.0,
          "metadata": {}
        }
      ]
    }
    ```

### 4. History & Trends
- `GET /history`
  - **Parameters:** `limit` (default: 50), `offset` (default: 0)
  - **Response (PaginatedHistoryResponseDTO):**
    ```json
    {
      "items": [
        {
          "run_id": "uuid",
          "target_model": "string",
          "status": "string",
          "started_at": "datetime",
          "completed_at": "datetime",
          "passed": true
        }
      ],
      "total": 0,
      "page": 1,
      "size": 50
    }
    ```

### 5. Operational
- `GET /health`
  - **Response:** `{"status": "ok", "timestamp": "..."}`
- `GET /versions`
  - **Response:** `{"service": "reporting-service", "version": "1.0.0"}`

## Invariants
- The API is strictly read-only.
- All requests are synchronous but computationally heavy requests (e.g. leaderboards) are backed by a cache abstraction.
