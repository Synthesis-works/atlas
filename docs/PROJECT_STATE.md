# Architecture State

## Architecture Diagram

```mermaid
graph TD
    Client[Web / API Client] --> API[FastAPI Gateway]
    API --> Auth[Auth Service]
    API --> Benchmarks[Benchmark Service]
    API --> Executions[Execution Service]
    
    Executions --> EventBus[Celery Event Bus]
    EventBus --> RedisBroker[(Redis)]
    
    RedisBroker --> CeleryWorker[Execution Worker]
    RedisBroker --> EvalWorker[Evaluation Worker]
    
    CeleryWorker --> Postgres[(PostgreSQL)]
    EvalWorker --> Postgres
    API --> Postgres
    
    CeleryWorker --> Executor[Executor Abstraction]
    Executor --> LocalExec[LocalExecutor (dev)]
    Executor --> DockerExec[DockerExecutor (prod)]
    DockerExec --> DockerEngine[(Docker Engine)]
    DockerEngine --> BenchmarkContainer[Benchmark Container]
    
    BenchmarkContainer --> LLM[LLM Providers]
```

## Service Dependency Graph
- **API** depends on -> PostgreSQL, Redis
- **Worker** depends on -> PostgreSQL, Redis, **Executor Runtime**
- **Scheduler** depends on -> Redis

## Database Dependency Graph
- `Alembic` manages schema over `PostgreSQL`. 
- Repositories (`packages/database/repositories`) abstract access for domain services.
- Data access is heavily injected into FastAPI routes via `Depends(get_db)`.

## Docker Dependency Graph
- `api` -> `db` (healthy), `redis` (healthy)
- `worker` -> `db` (healthy), `redis` (healthy), **Docker Engine (prod)**
- `scheduler` -> `db` (healthy), `redis` (healthy)

## Package Relationships
- `apps/backend` -> imports `services`, `packages`.
- `services/*` -> imports `packages/database`, `packages/llm`.
- `packages/*` -> independent foundational utilities.
- `packages/execution_engine/application` -> defines `Executor` interface, `LocalExecutor`, `DockerExecutor`.

## Flow Definitions
- **Execution flow**: Client -> API -> ExecutionService -> EventBus -> Worker -> Executor -> Database.
- **Worker flow**: Worker -> Pull from Redis -> Create Attempt -> Executor.execute() -> Persist ModelOutputs + Provenance -> Emit Evaluation Event.
- **Executor flow**: LocalExecutor (inline) OR DockerExecutor (container with security hardening) -> LLM Adapters -> JSON output lines -> Provenance telemetry.
- **Build flow**: `uv` resolves `uv.lock` -> Docker Multi-stage build syncs `.venv` -> Copies source -> Image generated.
- **Runtime flow**: `docker-compose up` -> DB/Redis Start -> API/Worker Start -> Alembic Migration (API container) -> Uvicorn serves traffic.
- **Deployment flow**: Production compose overrides dev volume binds, enforcing locked, read-only application containers and aggressive restart policies.
- **Production execution flow**: Requires dedicated Docker-capable runner host. Control plane never has Docker privileges.

## Execution Lifecycle (NEW)
```
Execution (QUEUED)
    ↓
ExecutionAttempt #1 (PENDING → CONTAINER_CREATED → RUNNING → COMPLETED/FAILED/TIMED_OUT/CANCELLED → CLEANED)
    ↓
ModelOutputs persisted per test case
    ↓
Provenance recorded: container_id, image_digest, timestamps, exit_code, termination_reason, cpu_seconds, peak_memory, pids_peak, network_rx/tx, trace_ids
    ↓
Outbox: ExecutionCompletedEvent
```