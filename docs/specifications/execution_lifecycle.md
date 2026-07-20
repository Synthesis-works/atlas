# Execution Lifecycle Specification

This document defines the lifecycle states and transitions for the Phase B Execution Engine. Execution is modeled as a robust, distributed state machine (Workflow Engine), rather than a standard CRUD resource.

## States

| State       | Description |
| ----------- | ----------- |
| `QUEUED`    | The execution has been submitted and is awaiting a worker to acquire a lease. |
| `SCHEDULED` | A worker has successfully acquired a lease and locked the execution. |
| `STARTING`  | The worker is downloading datasets, preparing models, and configuring the environment. |
| `RUNNING`   | The benchmark execution is actively processing. Heartbeats are expected. |
| `EVALUATING`| Model outputs are being graded against the execution's evaluation strategies. |
| `COMPLETED` | The execution finished successfully and all artifacts/scores are finalized. |
| `FAILED`    | The execution encountered a terminal error. |
| `RETRYING`  | The execution failed but is eligible for retry. The lease is released. |
| `CANCELLING`| A cancellation request has been received, waiting for worker to cleanly terminate. |
| `CANCELLED` | The execution was aborted by the user or system before completion. |

## Transition Matrix

| Current State | Action | Next State | Allowed |
| ------------- | ------ | ---------- | ------- |
| `QUEUED` | Worker Acquires Lease | `SCHEDULED` | ✅ |
| `QUEUED` | Cancel Request | `CANCELLED` | ✅ |
| `SCHEDULED` | Worker Initialization | `STARTING` | ✅ |
| `SCHEDULED` | Lease Expires/Fails | `RETRYING` or `FAILED` | ✅ |
| `STARTING` | Processing Begins | `RUNNING` | ✅ |
| `STARTING` | Cancel Request | `CANCELLING` | ✅ |
| `STARTING` | Initialization Fails | `RETRYING` or `FAILED` | ✅ |
| `RUNNING` | Processing Finishes | `EVALUATING` | ✅ |
| `RUNNING` | Cancel Request | `CANCELLING` | ✅ |
| `RUNNING` | Execution Fails | `RETRYING` or `FAILED` | ✅ |
| `RUNNING` | Lease Expires (No Heartbeat) | `RETRYING` or `FAILED` | ✅ |
| `EVALUATING` | Evaluation Finishes | `COMPLETED` | ✅ |
| `EVALUATING` | Evaluation Fails | `FAILED` | ✅ |
| `CANCELLING` | Worker Acknowledges | `CANCELLED` | ✅ |
| `RETRYING` | Re-queued | `QUEUED` | ✅ |
| `COMPLETED` | Any Action | — | ❌ |
| `FAILED` | Any Action | — | ❌ |
| `CANCELLED` | Any Action | — | ❌ |

## Invariants
- An execution has at most **one active lease** at any given time.
- A lease belongs to exactly **one execution**.
- `COMPLETED`, `FAILED`, and `CANCELLED` are terminal states. An execution in these states can never return to `RUNNING`.
- Every execution attempt is strictly immutable once finished.
- An execution cannot be created for a `DRAFT` benchmark version; the benchmark version must be `PUBLISHED`.
