# Subsystem Dependencies

This document maps the allowed dependencies between subsystems in Atlas to prevent circular dependencies.

```text
Execution Service
 ├── Database
 ├── Scheduler
 ├── Recovery Manager
 └── Health Service

Evaluation Service
 └── Execution Service

Reporting Service
 └── Evaluation Service

Frontend
 ├── Reporting Service
 ├── Execution Service
 └── Auth Service
```
