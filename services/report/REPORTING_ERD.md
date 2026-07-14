# Reporting ERD (Read-Only Context)

The Reporting Service primarily reads from the existing Atlas Database Schema. It defines minimal, if any, persistence of its own.

## External Dependencies (Read-Only)

```mermaid
erDiagram
    EvaluationSession ||--o{ AtlasRun : contains
    Project ||--o{ EvaluationSession : has
    AtlasRun ||--o{ ModelOutput : produces
    ModelOutput ||--|| EvaluationResult : evaluated_by
    AtlasRun ||--|| CapabilityProfile : assessed_as
    CapabilityProfile ||--o{ CapabilityScore : has
    
    Report ||--o{ ReportVersion : has
    ReportVersion ||--o{ ReportMetric : contains
```

## Internal Persistence (Future/If Needed)

If the Reporting Service eventually requires its own persistence (e.g., saving user-configured views), it would be strictly limited to:

```mermaid
erDiagram
    SavedDashboard {
        uuid id PK
        uuid user_id FK
        string name
        jsonb layout
    }
    
    SavedReportFilter {
        uuid id PK
        uuid user_id FK
        string name
        jsonb filters
    }
```
*Note: These internal tables are not implemented in the V1 read-only aggregation engine, as per the invariant "Reporting owns no state."*
