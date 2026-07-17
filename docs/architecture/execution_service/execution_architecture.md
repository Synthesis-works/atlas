# Execution Service Architecture

## Overview
The Execution Service is a dedicated subsystem within the Atlas platform responsible for orchestrating, managing, and monitoring the execution of benchmark runs against target models. It is fully decoupled from the Evaluation Service and the Benchmark configuration layer, acting as the sole owner of the execution lifecycle.

## Core Responsibilities
- **Run Orchestration:** Managing the lifecycle of an `AtlasRun` from creation to completion.
- **Scheduling & Quotas:** Enforcing concurrency limits, priorities, batching, and quotas.
- **Resource Dispatch:** Routing runs and tasks to the appropriate infrastructure via Execution Adapters (Local, Kubernetes, AWS Batch).
- **State Management:** Maintaining a robust state machine for Runs and Tasks.
- **Fault Tolerance:** Handling timeouts, retries, worker crashes, and stale executions through heartbeats and recovery mechanisms.
- **Artifact Management:** Collecting, persisting, and organizing logs, raw outputs, and artifacts generated during execution.

## System Components

### 1. API Layer
Exposes internal and external endpoints. External endpoints allow the Evaluation Service or CLI to trigger and monitor runs. Internal endpoints allow workers to check in, report progress, and upload artifacts.

### 2. Execution Controller
The brain of the service API. It receives requests, validates run configurations, creates database records, and interfaces with the Scheduler.

### 3. Scheduler
An independent component sitting between the Controller and the Task Queue. It owns:
- **Priorities & Fairness:** Determining which runs should execute first.
- **Concurrency Limits:** Ensuring target models or APIs are not overwhelmed.
- **Quotas:** Validating tenant/user limits before queuing tasks.
- **Batching & Retries:** Grouping tasks optimally and managing retry logic.

### 4. Task Queue / Dispatcher
Manages the distribution of work. Fed by the Scheduler, it uses Redis or PostgreSQL-based queuing to ensure tasks are picked up by available workers.

### 5. Worker Pool (Adapters)
Stateless workers that pull tasks, execute model inferences or benchmark logic, and report back to the API. They are environment-aware (e.g., a Kubernetes adapter spins up a job, a Local adapter spawns a process).

### 6. Recovery & Watchdog Daemon
A background process that scans the database for Runs/Tasks that are in `RUNNING` or `STARTING` states but haven't reported a heartbeat within the expected window. It transitions them to `FAILED`, `TIMEOUT`, or informs the Scheduler for requeuing.

## Subsystem Interactions

- **Evaluation Service -> Execution API:** Evaluation service requests a run and polls (or listens to events) for completion.
- **Execution API -> Scheduler:** API validates the request, sets state to `VALIDATING`, and hands off to the Scheduler.
- **Scheduler -> Task Queue -> Worker Pool:** The Scheduler prioritizes work, enforces limits, and pushes to the queue for workers.
- **Execution Service -> Database:** The service writes heavily to the database to persist state, progress, and logs. It relies on the Database as the source of truth.
