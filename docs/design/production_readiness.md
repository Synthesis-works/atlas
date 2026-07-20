# Phase A Production Readiness Review

*Hypothetical Scenario: Atlas scales to 10,000 active users tomorrow. What breaks?*

This document captures the known scaling assumptions and potential architectural bottlenecks of the Phase A (Benchmark Authoring) implementation. It is a historical record of technical debt and scaling risks to be addressed in future phases.

## 1. Storage & Dataset Size Limits
- **Assumption**: Datasets are external references (UUIDs) and versioned appropriately.
- **Risk**: As the number of benchmark versions explodes, the many-to-many relationship table `benchmark_version_dataset_link` will grow rapidly. 
- **Mitigation**: Ensure indexes exist on both `benchmark_version_id` and `dataset_version_id`. Consider archiving or soft-deleting old draft versions to prevent infinite row growth.

## 2. Event Throughput
- **Assumption**: `DomainEvent` tuples are currently yielded synchronously in the Application Service.
- **Risk**: If we hit 10,000 active users making concurrent mutations, the event dispatching (even if it's just logging) will block the main HTTP thread.
- **Mitigation**: Move the Event Publisher to a true async background task (e.g., Celery, Kafka, RabbitMQ) before relying on events for critical notifications or telemetry.

## 3. Long-Running Transactions & Lock Contention
- **Assumption**: Pessimistic locking (`get_for_update`) is used during state transitions (e.g. `PROPOSAL` -> `DRAFT`).
- **Risk**: The lock is held for the duration of the API request's database transaction. If the transaction takes too long (e.g. performing slow external validation before commit), other requests for the same Benchmark will pile up or time out.
- **Mitigation**: Keep the transaction scope strictly limited to the database `UPDATE`. Do any slow external I/O (like verifying a dataset exists via external API) *before* acquiring the row-level lock.

## 4. Pagination & Rate Limiting
- **Assumption**: `GET /projects/{id}/benchmarks` currently returns all rows.
- **Risk**: At 10,000 users, organizations with thousands of benchmarks will OOM the application server or cause massive JSON serialization latency.
- **Mitigation**: Enforce mandatory pagination (e.g., cursor or offset) on all list endpoints immediately in Phase B. Implement API Gateway rate-limiting to prevent scraping.

## 5. Queue Pressure (Forward-Looking to Phase B)
- **Assumption**: Phase A does not execute benchmarks, but Phase B will.
- **Risk**: 10,000 users clicking "Run Benchmark" will instantly overwhelm any synchronous scheduling mechanism.
- **Mitigation**: Phase B must be designed as a distributed state machine (Workflow Engine) utilizing decoupled worker nodes, leases, and asynchronous queues.

## Conclusion
Phase A is architecturally sound for its current scope, but requires pagination, asynchronous event routing, and careful transaction management before it can be considered hyper-scale production ready.
