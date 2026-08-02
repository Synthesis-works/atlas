# Architecture Decisions Log

This document records major architectural decisions made during the development of Project Atlas. 
Keeping this log helps future contributors understand *why* certain patterns were adopted, preventing them from being accidentally removed or reinvented.

## 1. The Command Pattern (Execution Service)
**Decision**: The Execution Service API layer delegates entirely to specific Commands (e.g., `CreateRunCommand`, `ClaimTasksCommand`) which are handled by focused Controllers.
**Reasoning**: This prevents business logic from bleeding into the HTTP routing layer. It allows CLI tools, background schedulers, and HTTP APIs to invoke the exact same execution logic without duplicating code.

## 2. Event Sourcing for Execution Runs
**Decision**: Every state transition in the Execution Service creates an immutable `RunEvent` (e.g., `RUN_CREATED`, `TASK_ASSIGNED`).
**Reasoning**: Execution is inherently distributed and asynchronous. A strict event log is required for debugging failed runs, powering UI timelines, supporting Server-Sent Events (SSE) streaming to clients, and auditability.

## 3. Atomic Task Claiming
**Decision**: Workers claim tasks using pessimistic database locking (e.g., `FOR UPDATE SKIP LOCKED`).
**Reasoning**: In a distributed environment with multiple workers competing for tasks, this prevents the catastrophic "double execution" problem where two workers process the same LLM inference task simultaneously, which would waste money and corrupt output records.

## 4. Exclusive Task Ownership
**Decision**: A task is exclusively owned by the worker that claimed it. `CompleteTaskCommand` and `FailTaskCommand` strictly verify `worker_id == assigned_worker_id`.
**Reasoning**: Prevents rogue, timed-out, or imposter workers from interfering with tasks they no longer (or never did) own. This ensures deterministic state transitions.

## 5. Scheduler vs Controller Segregation
**Decision**: The Execution Controller manages pure state transitions. The Scheduler manages purely *who* gets *what* and *when*. The Scheduler does not mutate task state directly, nor does it decide on retries.
**Reasoning**: Scheduling is extremely complex (fairness, quotas, priorities). By keeping the Execution Controller entirely ignorant of scheduling logic, we can easily swap, test, and upgrade the Scheduler without breaking the core execution guarantees.
