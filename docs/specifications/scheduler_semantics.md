# Scheduler & Sweeper Semantics (Phase B)

This document defines the operational characteristics of the background processes responsible for sweeping expired leases and managing retry orchestration.

## 1. Cadence and Sweeping
- **Sweep Frequency**: The sweeper runs on a configurable cadence (defaulting to 30-60 seconds) to detect leases where `expires_at < now()`. This is governed by application configuration to allow operational tuning without code changes.
- **Clock Drift Tolerance**: To prevent thrashing due to minor clock drift between instances, the sweeper evaluates expiry using the database's transactional time or a unified clock dependency (`clock.now()`), optionally padded with a strict 5-second grace period.

## 2. Idempotency and Concurrency
- **Concurrent Schedulers**: The sweeper is designed to run safely across multiple instances simultaneously.
- **Locking**: It queries for expired leases using `SELECT ... FOR UPDATE SKIP LOCKED`. If another scheduler instance is already processing an expired lease, the query simply skips it, guaranteeing no double-processing.
- **Idempotency Guarantee**: If a lease is swept, the Domain Service's `expire_lease` method is idempotent. If the execution has already been failed or retried by another thread, the transition is ignored safely.

## 3. Retry Timing and Semantics
- **Decision Ownership**: The Scheduler *does not* decide whether to retry. It merely invokes `domain_service.expire_lease()`. The domain aggregate evaluates its `max_retries` rule to determine the transition (`RETRYING` or `FAILED`).
- **Retry Timing**: In the initial v1 implementation, retries are immediate. When an attempt fails and retry is permitted, the execution transitions back to `QUEUED` and is instantly available for the next worker to `acquire`.
- *(Future Enhancement: Exponential backoff can be added by introducing a `visible_after` timestamp on the execution).*

## 4. Crash Recovery and Transactional Boundaries
- **At-Least-Once Delivery**: The sweeper operates under an at-least-once model. If the sweeper crashes midway through failing a lease, the database transaction rolls back, and the next sweep interval will pick it up again.
- **Worker Crashes**: If a worker node goes OOM or loses network connectivity, its lease simply expires naturally on the backend. The sweeper will detect this and recover the execution without manual intervention.
- **Batch Processing**: The scheduler processes sweeps on a *best-effort, independent* basis. If execution #1 fails to persist, executions #2-50 are still processed independently.
- **Publish Failure**: Because events are published *after* database commit (until an Outbox pattern is introduced), a failure during event publishing does NOT roll back the database transaction. Tests and operational monitors should not expect rollback on publish failure.

## 5. Domain Events
Events emitted by a single aggregate preserve causal order strictly. When a lease expires, the sequence is:
1. `LeaseExpiredEvent`
2. `ExecutionRetryEvent` (if retries remain) OR `ExecutionFailedEvent` (if exhausted).
