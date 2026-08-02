# Execution State Machine

The Execution Service manages state across two primary entities: `AtlasRun` (the global execution batch) and `AtlasTask` (the individual sub-tasks, typically mapping to test cases).

## AtlasRun State Machine

A Run can be in one of the following states:

- **CREATED:** The run has been initialized in the database but is not yet validated.
- **VALIDATING:** Verifying that the benchmark, adapter, model, dataset, and configuration exist and that the user has the necessary permissions and quota.
- **QUEUED:** Validated and waiting in the dispatch queue (managed by the Scheduler) for resources to become available.
- **STARTING:** The adapter is allocating resources (e.g., spinning up pods, downloading images).
- **RUNNING:** Active task execution is underway. At least one task is being processed.
- **PAUSED:** The run has been paused (either manually by the user, or automatically due to rate limits/budget).
- **COMPLETED:** All tasks finished successfully. (Terminal)
- **FAILED:** The run encountered a fatal error, validation failed, or tasks failed and retries were exhausted. (Terminal)
- **CANCELLED:** The run was aborted by a user or system command. (Terminal)
- **TIMEOUT:** The run exceeded its global maximum execution time. (Terminal)

### Run Transitions
```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> VALIDATING : Trigger Validation
    VALIDATING --> QUEUED : Validation Passed
    VALIDATING --> FAILED : Validation Failed
    QUEUED --> STARTING : Resources Allocated (Scheduler)
    STARTING --> RUNNING : Worker Ready
    RUNNING --> PAUSED : Pause Signal
    PAUSED --> RUNNING : Resume Signal
    
    RUNNING --> COMPLETED : All Tasks Success
    RUNNING --> FAILED : Fatal Error / Fail Fast
    RUNNING --> TIMEOUT : Global Timeout Exceeded
    
    VALIDATING --> CANCELLED : Cancel Signal
    QUEUED --> CANCELLED : Cancel Signal
    STARTING --> CANCELLED : Cancel Signal
    RUNNING --> CANCELLED : Cancel Signal
    PAUSED --> CANCELLED : Cancel Signal

    COMPLETED --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
    TIMEOUT --> [*]
```

## AtlasTask State Machine

A Task (mapping to a specific test case evaluation) has a narrower state machine:

- **QUEUED:** Waiting to be claimed by a worker.
- **RUNNING:** Claimed by a worker, inference in progress.
- **COMPLETED:** Result successfully generated. (Terminal)
- **FAILED:** Task failed (Terminal if max_retries reached).
- **TIMEOUT:** Task exceeded its individual timeout. (Terminal)

### Task Transitions
```mermaid
stateDiagram-v2
    [*] --> QUEUED
    QUEUED --> RUNNING : Worker Claims Task
    RUNNING --> COMPLETED : Success
    RUNNING --> FAILED : Execution Error
    RUNNING --> TIMEOUT : Task Timeout / Heartbeat Loss
    
    FAILED --> QUEUED : Retry via Scheduler (if retry_count < max)
    TIMEOUT --> QUEUED : Retry via Scheduler (if retry_count < max)
    
    COMPLETED --> [*]
    FAILED --> [*] : Retries Exhausted
    TIMEOUT --> [*] : Retries Exhausted
```
