# Reporting Dataflow

```mermaid
sequenceDiagram
    participant Client
    participant Router as API Router
    participant Controller
    participant Service as Reporting Service
    participant Cache as ReportCache
    participant QuerySvc as Query Service
    participant Repo as Reporting Repository
    participant DB as Database (PostgreSQL)

    Client->>Router: GET /leaderboards?strategy=overall
    Router->>Controller: get_leaderboard(strategy="overall")
    Controller->>Service: fetch_leaderboard(strategy="overall")
    
    Service->>Cache: get("leaderboard:overall")
    alt Cache Miss
        Service->>QuerySvc: get_leaderboard(strategy="overall")
        QuerySvc->>Repo: execute_query(...)
        Repo->>DB: SQL SELECT ...
        DB-->>Repo: Raw DB Rows
        Repo-->>QuerySvc: DB Models
        QuerySvc-->>Service: Read Models
        Service->>Cache: set("leaderboard:overall", Read Models)
    else Cache Hit
        Cache-->>Service: Read Models
    end
    
    Service-->>Controller: Read Models
    Controller->>Controller: map Read Models to API DTOs
    Controller-->>Router: API DTOs (JSON)
    Router-->>Client: 200 OK (JSON)
```

## Key Flows
1. **API to Controller:** Input validation (via Pydantic DTOs).
2. **Controller to Service:** Business operation request.
3. **Service to Cache:** Check for cached Read Models.
4. **Service to Query Service:** If cache miss, delegate to the specific query service.
5. **Query Service to Repo:** Formulate data request based on domain logic.
6. **Repo to DB:** SQLAlchemy execution.
7. **Return Path:** DB Models are mapped to Read Models by the Query Service. Read Models are cached by the Service, then mapped to API DTOs by the Controller.
