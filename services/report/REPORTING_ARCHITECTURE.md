# Reporting Architecture

## Overview

The Atlas Reporting Service is a read-only aggregation engine that provides insights, dashboards, leaderboards, and trend analysis over the raw data produced by the Execution and Evaluation subsystems.

## Layered Architecture

The service strictly adheres to a layered architecture to ensure separation of concerns, testability, and future scalability.

```text
       [ API Client ]
             │
      (HTTP Requests)
             ▼
    ┌────────────────┐
    │  Reporting API │ (FastAPI Routers)
    └───────┬────────┘
            │
            ▼
 ┌──────────────────────┐
 │ Reporting Controller │ (Orchestration & DTO mapping)
 └──────────┬───────────┘
            │
            ▼
   ┌──────────────────┐
   │ Reporting Service│ (Business logic, Cache abstraction, Exporters)
   └────────┬─────────┘
            │
            ▼
  ┌───────────────────┐
  │   Query Services  │ (Domain-specific queries: Leaderboard, Trends)
  └─────────┬─────────┘
            │
            ▼
┌───────────────────────┐
│ Reporting Repository  │ (Data access abstraction)
└───────────┬───────────┘
            │
            ▼
      [ PostgreSQL ]
```

## Core Components

- **Reporting API (Routers):** Thin FastAPI routers defining the HTTP endpoints.
- **Reporting Controllers:** Orchestrate requests, delegate to services, and map Read Models to API DTOs.
- **Reporting Service:** The business logic layer. It coordinates Query Services, Trend Analyzers, Leaderboard Strategies, and Cache abstractions.
- **Query Services:** Specialized services (e.g., `LeaderboardQueryService`, `TrendQueryService`) that own a single read domain.
- **Reporting Repository:** The lowest layer interacting directly with SQLAlchemy and the database.
- **Read Models & DTOs:** Internal read models represent the aggregated data structures, while API DTOs are the exact schemas returned over HTTP, shielding the API from internal schema changes.
- **Cache Abstraction:** A `ReportCache` interface allowing future integration of Redis or other caching systems without changing business logic.
- **Exporters:** Interfaces (`CSVExporter`, `JSONExporter`) for exporting report data.

## Boundaries
- Depends on `packages/database` for DB connections and base SQLAlchemy models.
- Does not modify any state in `Execution` or `Evaluation`.
