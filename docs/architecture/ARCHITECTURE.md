# Architecture Overview

Atlas is designed with a strict microservice boundary philosophy.

## The Principle of Ownership
- **Execution Service** owns "What happened."
- **Evaluation Service** owns "How good was it."
- **Reporting Service** owns "How do we present it."

## Execution Engine Architecture
The Execution Engine is completely event-driven, decoupled, and highly resilient.

### Key Components
1. **Database Foundation**: SQLAlchemy core holding state and history.
2. **Controllers**: `RunController`, `TaskController`, `WorkerController`. The ONLY entities permitted to mutate state.
3. **AtlasScheduler**: A detached polling engine that emits `SchedulingDecision` objects (does not mutate state).
4. **RecoveryManager**: A detached watchdog that issues explicit failure facts (does not mutate state or claim tasks).
5. **EventPublisher**: All state transitions emit an append-only `RunEvent`.

See [Integration Invariants](INTEGRATION_INVARIANTS.md) and [Subsystem Dependencies](SUBSYSTEM_DEPENDENCIES.md) for deeper architectural guidelines.
