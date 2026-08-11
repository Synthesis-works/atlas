# Docker Setup & Architecture

This guide details how to run the Atlas evaluation platform using Docker.

## Architecture

The Dockerized environment consists of the following services:

1. **db**: PostgreSQL database (Core relational store).
2. **redis**: Redis server (Message broker for Celery and caching).
3. **api**: FastAPI application serving REST endpoints on port `8000`.
4. **worker**: Celery worker instance that executes background tasks (e.g., executing models).
5. **scheduler**: Celery beat scheduler for periodic tasks.
6. **frontend**: Next.js frontend application serving UI on port `3000`.

### Startup Order
Services have strict dependency trees managed by Docker Compose:
`postgres` & `redis` start first.
`api`, `worker`, and `scheduler` wait for health checks from `db` and `redis` before starting.
The `api` container automatically applies database migrations using Alembic on startup.

## Commands

### Local Development
To start the entire stack with hot-reloading for local development:
```bash
docker-compose up --build
```
This maps your local source code into the containers, meaning any code edits will instantly reload the API and workers.

To stop the services:
```bash
docker-compose down
```

To wipe the database entirely (destroying volumes):
```bash
docker-compose down -v
```

### Production Deployment
For production, use the `docker-compose.prod.yml` file, which disables volume binding for source code and configures proper restart policies.

Ensure you set `.env` with secure secrets before starting:
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

## Troubleshooting

- **Database Connections Failing**: If `api` or `worker` crash complaining about database connection, ensure `DATABASE_URL` is set to `postgresql://postgres:postgres@db:5432/atlas`.
- **Migrations Not Running**: The API container attempts to run `python -m alembic upgrade head` on startup. If this fails, view the `api` logs to diagnose syntax errors in models.
- **Code Changes Not Reflecting**: Ensure you are using `docker-compose.yml` (and not `prod.yml`) as it contains the `volumes: - .:/app` binding.

## Canonical Local Frontend Development

**Canonical Repository:** `C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter`
**Frontend Directory:** `apps/landing`
**Dev Command:** `npm --prefix apps/landing run dev`
**Canonical Dev URL:** `http://127.0.0.1:5173`
**Diagnostic Endpoint:** `http://127.0.0.1:5173/__atlas_dev`

> **IMPORTANT:** Do not use `localhost` or launch secondary Atlas checkouts on port `5173`. Port 5173 conflict checks automatically block secondary servers from starting on conflicting paths.
