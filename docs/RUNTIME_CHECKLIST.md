# Runtime Validation Checklist

Before any infrastructure pull request is merged, it must pass this explicit checklist on a host machine with Docker Engine installed.

### 1. Docker & Compose
- [ ] `docker compose config` parses without errors or warnings.
- [ ] `docker compose -f docker-compose.prod.yml config` parses correctly.
- [ ] `docker compose build` successfully leverages `uv` caching and completes without failing.

### 2. Infrastructure Services
- [ ] **Database**: Postgres initializes, creates the `atlas` database, and becomes `healthy`.
- [ ] **Redis**: Redis initializes and becomes `healthy`.
- [ ] **Volumes**: Data is preserved across a container restart (e.g., `docker compose stop && docker compose start`).

### 3. Application Services
- [ ] **API**: FastAPI starts successfully and binds to port 8000.
- [ ] **Workers**: Celery worker discovers tasks and successfully connects to Redis.
- [ ] **Scheduler**: Celery beat starts correctly and begins pinging/polling.
- [ ] **Alembic**: The `bash` startup command correctly executes migrations against the Postgres DB, resulting in populated tables.

### 4. Health Checks & Networking
- [ ] The `api` container transitions to `healthy` status via the `/api/v1/health` endpoint.
- [ ] Containers communicate purely via internal service names (e.g., `db`, `redis`), no hardcoded `localhost` inside application logic.

### 5. Environment Variables & Security
- [ ] `DATABASE_URL` is successfully overridden from `.env.example`.
- [ ] Images run as the non-root `atlas` user (verify via `docker exec -it <container_name> whoami`).

### 6. Performance
- [ ] Rebuilding the image after a source code change takes < 10 seconds due to successful layer caching of the `.venv` directory.
