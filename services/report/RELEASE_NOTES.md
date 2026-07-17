# Release Notes - v0.7-reporting-core

## Overview
This release finalizes the core Reporting subsystem for Atlas. It acts as the backbone for the aggregation and presentation layer of the Evaluation Operating System.

## Features Added
- **Reporting API:** Thin, highly-focused FastAPI routers covering leaderboards, capabilities, history, and operational endpoints.
- **Layered Architecture:** Full implementation of Controllers, Reporting Services, Query Services, and Repositories.
- **Model Abstraction:** Complete separation of DB Models, Read Models, and API DTOs to prevent database schema leakage.
- **Extensible Strategies:** Implementation of `LeaderboardStrategy` and `TrendAnalyzer` abstractions.
- **Cache Abstraction:** Introduction of `ReportCache` to prepare for high-concurrency loads without current-day overhead.
- **Exporters:** Support for JSON and CSV data exports via the `Exporter` interface.

## Architectural Enforcements
- Verified that the Reporting Service is strictly read-only and owns no domain state.
- Verified that all data access occurs through the `ReportingRepository`.

## Deferred
- Custom `SavedReport` and `Dashboard` definition persistence.
- Redis caching implementation (noop cache is used for v0.7).
- Advanced exporters (e.g., Parquet).

## Maturity
The Database, Execution, Evaluation, and now Reporting subsystems are considered stable core components. The next focus for the platform will be the Dataset Service.
