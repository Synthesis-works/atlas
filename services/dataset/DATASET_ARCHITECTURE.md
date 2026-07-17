# Dataset Architecture

## Overview
The Atlas Dataset Service is a foundational upstream component. It owns the ingestion, validation, versioning, cleaning, licensing, lineage, and publishing of evaluation datasets. Downstream services (Authoring, Execution, Evaluation, Reporting) consume published dataset versions but cannot mutate them.

## Layered Architecture

```text
       [ API Client ]
             │
             ▼
    ┌────────────────┐
    │  Dataset API   │ (FastAPI Routers)
    └───────┬────────┘
             │
             ▼
 ┌──────────────────────┐
 │  Dataset Controller  │ (Orchestration & DTO mapping)
 └──────────┬───────────┘
             │
             ▼
   ┌──────────────────┐
   │ Dataset Services │ (Upload, Validate, Clean, Version, Publish)
   └────────┬─────────┘
             │
             ▼
   ┌──────────────────┐
   │ Core Abstractions│ (ValidationRule, CleaningPipeline, Importer)
   └────────┬─────────┘
             │
             ▼
 ┌──────────────────────┐
 │  Dataset Repository  │ (Data access abstraction)
 └───────────┬──────────┘
             │
             ▼
       [ PostgreSQL ]
```

## Core Abstractions

- **StorageProvider:** Manages physical file storage. Currently limited to `LocalStorageProvider`, with a path for S3/GCS.
- **DatasetImporter:** Defines standard import routines (`CSVImporter`, `JSONImporter`).
- **ValidationRule:** Small, composable rules (e.g. `RequiredColumnsRule`) run by the ValidationService.
- **CleaningPipeline:** A sequence of transformations (e.g. `NormalizeWhitespace`) executed by the CleaningService.

## Boundaries
- Depends on `packages/database` for base models.
- Does not import or know about Execution, Evaluation, or Reporting modules.
