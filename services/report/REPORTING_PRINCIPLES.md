# Reporting Principles

1. **Read-Only by Default:** The reporting service exists to query, aggregate, and present. It does not mutate the core domain (runs, evaluations).
2. **Layered Data Representation:**
   - **Database Models:** Raw SQLAlchemy entities mapping exactly to DB tables.
   - **Read Models:** Aggregated, joined, and computed internal structures optimized for reporting logic.
   - **API DTOs:** The final JSON-serializable output schema contract with the client.
3. **Decoupled Data Access:** Never build raw SQL or SQLAlchemy queries inside controllers or business services. Always use a `QueryService` interacting with a `Repository`.
4. **Cache-Ready:** All computationally expensive queries or aggregations must interface with a cache abstraction (`ReportCache`), ensuring simple future performance scaling.
5. **Extensibility:** Leaderboards and Trends are complex domains. Use abstractions like `LeaderboardStrategy` and `TrendAnalyzer` to handle various calculation requirements without cluttering controllers.
6. **Unified Exports:** Data exports (CSV, JSON) are a core reporting feature, backed by generic Exporter interfaces to easily add new formats like Parquet in the future.
