# Reporting Invariants

1. **Reporting owns no state.**
   - The Reporting Service is completely read-only with respect to domain data.
   - It never stores evaluations, metrics, runs, or capabilities.
   - It only derives views from the existing data in Execution and Evaluation.
2. **Normalized entities are restricted.**
   - No new normalized entities should be created unless absolutely necessary.
   - The only permitted persistence for Reporting involves user-saved views: `SavedReport`, `SavedReportFilter`, `SavedDashboard`.
   - Everything else must come directly from Execution and Evaluation tables.
3. **Strict separation of concerns.**
   - Database Models -> Read Models -> API DTOs.
   - This prevents the database schema from leaking into the API layer.
4. **Abstracted Data Access.**
   - Controllers must not construct SQL queries.
   - Data access is mediated through `QueryServices` and `Repositories`.
