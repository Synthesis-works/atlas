# Execution Sequence Diagrams

These sequence diagrams illustrate the distributed interactions between the User, the Control Plane (Public API), the Data Plane (Worker API / Service), and the external Worker Nodes.

## 1. Happy Path: Queue to Completion
```mermaid
sequenceDiagram
    actor User
    participant ControlPlane as API / Application Service
    participant Database
    participant WorkerAPI as Internal Worker API
    participant Worker as Worker Node

    User->>ControlPlane: POST /benchmarks/{id}/executions
    ControlPlane->>Database: Insert Execution (status=QUEUED)
    ControlPlane-->>User: 201 Created (id)
    
    loop Every 5s
        Worker->>WorkerAPI: POST /acquire
        WorkerAPI->>Database: Select for Update (get QUEUED)
        WorkerAPI->>Database: Update Execution (status=SCHEDULED, lease created)
        WorkerAPI-->>Worker: 200 OK (execution_id, lease_id)
    end
    
    Worker->>WorkerAPI: POST /heartbeat (status=STARTING)
    WorkerAPI->>Database: Update Execution
    
    Worker->>Worker: Run Benchmark
    
    loop Every 30s
        Worker->>WorkerAPI: POST /heartbeat (status=RUNNING)
        WorkerAPI->>Database: Update Lease (extend expires_at)
        WorkerAPI-->>Worker: 200 OK (action=CONTINUE)
    end
    
    Worker->>WorkerAPI: POST /complete (status=COMPLETED)
    WorkerAPI->>Database: Update Execution (status=EVALUATING)
    WorkerAPI-->>Worker: 200 OK
```

## 2. Cancellation Flow
```mermaid
sequenceDiagram
    actor User
    participant ControlPlane
    participant Database
    participant WorkerAPI
    participant Worker

    User->>ControlPlane: POST /executions/{id}/cancel
    ControlPlane->>Database: Update Execution (status=CANCELLING)
    ControlPlane-->>User: 202 Accepted
    
    Note over Worker, WorkerAPI: Worker is already running
    
    Worker->>WorkerAPI: POST /heartbeat
    WorkerAPI->>Database: Read Execution (status=CANCELLING)
    WorkerAPI-->>Worker: 200 OK (action=CANCEL)
    
    Worker->>Worker: Abort processes cleanly
    
    Worker->>WorkerAPI: POST /complete (status=CANCELLED)
    WorkerAPI->>Database: Update Execution (status=CANCELLED)
    WorkerAPI-->>Worker: 200 OK
```

## 3. Worker Crash (Orphaned Lease)
```mermaid
sequenceDiagram
    participant ControlPlane
    participant Database
    participant Worker
    participant Sweeper as Background Sweeper Task

    Worker->>ControlPlane: (Acquires Lease)
    Worker->>Worker: (Crashes, stops sending heartbeats)
    
    loop Every 1m
        Sweeper->>Database: Find Leases where expires_at < NOW()
        Sweeper->>Database: Update Execution (status=RETRYING, delete lease)
    end
```
