# State Machine Reference

This document maps the allowed state transitions for the core entities in the Execution Service. Any transition not documented here is strictly prohibited and should throw a `ValueError` or `IllegalStateTransitionError`.

## AtlasRun Lifecycle
```mermaid
stateDiagram-v2
    [*] --> CREATED: CreateRunCommand
    CREATED --> VALIDATING: ValidateRunCommand
    VALIDATING --> QUEUED: Validation Success
    VALIDATING --> FAILED: Validation Failure
    QUEUED --> RUNNING: Task Started
    QUEUED --> CANCELLED: CancelRunCommand
    RUNNING --> PAUSED: PauseRunCommand
    RUNNING --> FAILED: Too Many Task Failures
    RUNNING --> COMPLETED: All Tasks Finished
    RUNNING --> CANCELLED: CancelRunCommand
    PAUSED --> RUNNING: ResumeRunCommand
    PAUSED --> CANCELLED: CancelRunCommand
    FAILED --> VALIDATING: RetryRunCommand
    CANCELLED --> [*]
    COMPLETED --> [*]
    FAILED --> [*]
```

## AtlasTask Lifecycle
```mermaid
stateDiagram-v2
    [*] --> PENDING: Created with Run
    PENDING --> RUNNING: ClaimTasksCommand (Atomic)
    RUNNING --> COMPLETED: CompleteTaskCommand
    RUNNING --> FAILED: FailTaskCommand
    RUNNING --> CANCELLED: Run Cancelled
    FAILED --> PENDING: Retry Run/Task
    COMPLETED --> [*]
    CANCELLED --> [*]
```

## ExecutionWorker Lifecycle
```mermaid
stateDiagram-v2
    [*] --> REGISTERED: RegisterWorkerCommand
    REGISTERED --> READY: Heartbeat (Healthy)
    READY --> BUSY: Task Assignment (Future Load Tracking)
    BUSY --> READY: Task Completion
    READY --> OFFLINE: Watchdog Timeout / Heartbeat (Unhealthy)
    BUSY --> OFFLINE: Watchdog Timeout / Heartbeat (Unhealthy)
    OFFLINE --> READY: Heartbeat (Healthy)
    OFFLINE --> [*]
```
