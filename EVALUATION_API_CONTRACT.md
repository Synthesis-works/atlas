# Evaluation API Contract

The Evaluation Service exposes a read-only reporting API. All mutations (Job Creation, Metric Processing, Capability Scoring) are handled internally via the Orchestrator listening to internal Domain Events.

## Base URL
`/reports`

## Endpoints

### 1. Get Evaluation Report
`GET /evaluations/{job_id}`
Returns the full evaluation tree including all attempts, pipelines executed, and raw/normalized metric values.

**Response**:
```json
{
  "job_id": "uuid",
  "run_id": "uuid",
  "status": "COMPLETED",
  "attempts": [
    {
      "attempt_id": "uuid",
      "status": "COMPLETED",
      "pipeline_version_id": "uuid",
      "results": [
        {
          "result_id": "uuid",
          "metrics": [
            {
              "name": "pass_rate",
              "value": 1.0,
              "normalized": 1.0
            }
          ]
        }
      ]
    }
  ]
}
```

### 2. Get Capability Profile
`GET /capabilities/{adapter_version_id}`
Returns the aggregated intelligence capabilities derived from the underlying metric evaluations for a given model/adapter.

**Response**:
```json
{
  "adapter_version_id": "uuid",
  "scores": [
    {
      "capability": "Coding",
      "score": 0.95
    },
    {
      "capability": "Reasoning",
      "score": 0.85
    }
  ]
}
```

### 3. Get Leaderboard
`GET /leaderboard`
Returns an aggregated ranking of all evaluated adapters based on their mean capability scores.

**Response**:
```json
[
  {
    "adapter": "gemini-1.5-pro (v1.0)",
    "overall_score": 0.92
  }
]
```

### 4. Get Metrics Dictionary
`GET /metrics`
Returns the definitions of all available metrics across the system.

**Response**:
```json
[
  {
    "name": "pass_rate",
    "category": "CORRECTNESS",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent"
  }
]
```
