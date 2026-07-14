# Integration Invariants

This document governs the integration and cross-subsystem boundaries across the Execution Service.
Breaking these rules will result in tightly coupled, brittle subsystems.

## State Transitions
* Scheduler never changes Run or Task state directly.
* Recovery Manager never changes Run or Task state, nor does it claim tasks.
* Workers never update Run or Task state directly in the database.
* Controllers (RunController, TaskController, WorkerController) exclusively own all database transactions and lifecycle state changes.

## Data & Event Integrity
* Events are strictly append-only.
* Evaluation only consumes terminal runs (`COMPLETED`, `FAILED`, `CANCELLED`).
* Reporting never modifies execution state; it is strictly a read-only consumer of events.

## API & Web Layer
* The Web/HTTP Router must never contain business logic, SQL queries, or scheduling logic.
* The Web Router is purely a delegation adapter to Controllers and Services (e.g., `HealthService`).
