# Reliable Event Delivery (Outbox Pattern)

## 1. Product Specification

### 1.1 Reliability Guarantees
The Atlas event pipeline provides **At-Least-Once** delivery guarantees for all domain events. Exactly-once is practically impossible to guarantee in distributed systems over unreliable networks, so we rely on consumer idempotency.

> **Architecture Rule A-003**
> 
> **Every Outbox consumer MUST be idempotent.**
> Duplicate event delivery is expected behavior. Subscribers must detect and safely ignore duplicates.

### 1.2 Event Lifecycle & Dispatch
The domain event has already happened. The only thing becoming asynchronous is **delivery**. Asynchronous delivery begins only after a successful transaction commit.

```text
Execution Aggregate
        ↓
ExecutionCompletedEvent created
        ↓
Repository.save()
        ↓
Aggregate persisted
        ↓
Outbox persisted
        ↓
COMMIT
        ↓
Return success to caller
        ↓
Background dispatcher
        ↓
CompositeEventPublisher
        ↓
Subscribers
```

### 1.3 Failure Handling & Retries
- **Dispatch Failure**: If an event fails to dispatch to any subscriber, the event remains in the outbox in a `PENDING` or `FAILED` state.
- **Retries**: A background sweeper (the Outbox Dispatcher) continually polls for unprocessed events and re-attempts delivery.
- **Backoff Strategy**: Failed events follow an exponential backoff schedule. 
- **Poison Messages**: After a maximum number of attempts (e.g., 10), the event is moved to a `DEAD_LETTER` terminal state to prevent corrupted payloads from spinning forever. It requires manual intervention to resolve.

### 1.4 Ordering Guarantees
- **Per-Aggregate Ordering**: Guaranteed. Events belonging to the same aggregate (e.g., the same Execution) will be dispatched in the order they occurred.
- **Global Ordering**: Not guaranteed. Events from different aggregates may be interleaved.

### 1.5 Event Envelope Serialization
To remain language-agnostic and prepare for future distributed message buses (e.g., Kafka), outbox payloads use an explicit schema:
```json
{
  "schema_version": 1,
  "event_id": "<uuid>",
  "event_type": "ExecutionCompletedEvent",
  "event_version": 1,
  "aggregate_id": "<uuid>",
  "aggregate_type": "Execution",
  "occurred_at": "<timestamp>",
  "trace_context": {
      "correlation_id": "...",
      "trace_id": "..."
  },
  "payload": {
      "execution_id": "...",
      "attempt_id": "..."
  }
}
```

---

## 2. Architecture Review

### 2.1 The Outbox Table Schema
```sql
CREATE TABLE outbox_messages (
    outbox_message_id UUID PRIMARY KEY,
    event_id UUID NOT NULL,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    schema_version INTEGER NOT NULL DEFAULT 1,
    payload JSONB NOT NULL,
    trace_context JSONB NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE NULL,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2.2 Transaction Boundary

```text
=======================================
          TRANSACTION BOUNDARY
=======================================
BEGIN TRANSACTION
        ↓
Save Aggregate State
        ↓
Insert Outbox Rows
        ↓
COMMIT
=======================================
        ↓
Background Dispatcher
        ↓
Publish to Subscribers
```

### 2.3 Dispatcher Lifecycle & Concurrency
A dedicated background daemon (or Celery task running periodically) acts as the **Outbox Dispatcher**:
1. Locks a batch of `PENDING` (or due-for-retry) messages using `SELECT ... FOR UPDATE SKIP LOCKED`.
2. Hands the batch to the `CompositeEventPublisher`.
3. If successful, marks as `PROCESSED`. If it throws, increments `retry_count`, calculates `next_retry_at`, and releases the lock.

**Dispatcher Concurrency**: Multiple dispatcher instances are fully supported. Because we use `SKIP LOCKED`, Dispatcher 1, Dispatcher 2, and Dispatcher 3 can safely run simultaneously without processing the same messages.

### 2.4 Configuration
The dispatcher relies on configurable environment variables to govern load:
- `OUTBOX_BATCH_SIZE=100` (Number of events to pull per sweep)
- `OUTBOX_POLL_INTERVAL=5` (Seconds between sweeps)

### 2.5 Cleanup and Retention Policy
A separate background cron will reap `PROCESSED` messages older than 7 days to prevent unbounded table growth. `DEAD_LETTER` messages are retained indefinitely until manually resolved.
