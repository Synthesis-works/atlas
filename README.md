# Project Atlas

Atlas is a next-generation distributed evaluation platform for LLMs.

## What Atlas Is
Atlas orchestrates complex benchmarking workflows by managing execution, scheduling tasks to distributed workers, recovering from failures, and reliably feeding evaluation results to reporting mechanisms.

## Quick Start
To get started locally, you can use our one-command setup scripts:

For Windows (PowerShell):
```powershell
.\scripts\run_demo.ps1
```

## Architecture
Atlas is composed of several independent microservices ensuring modularity, clear boundaries, and robust failure handling.
- **Execution Service**: The engine of Atlas. Owns "What happened".
- **Evaluation Service**: Assesses outcomes. Owns "How good was it".
- **Reporting Service**: Aggregates metrics. Owns "How do we present it".

See [Architecture Overview](docs/architecture/ARCHITECTURE.md) for more details.

## Contributing
1. Ensure you read the [Integration Invariants](docs/architecture/INTEGRATION_INVARIANTS.md).
2. Familiarize yourself with the [Execution API Contract](docs/architecture/EXECUTION_API_CONTRACT.md) before interacting with Execution.

## Links
- [Subsystem Dependencies](docs/architecture/SUBSYSTEM_DEPENDENCIES.md)
