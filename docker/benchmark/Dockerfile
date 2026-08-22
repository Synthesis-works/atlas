# syntax=docker/dockerfile:1
# Atlas benchmark execution image.
#
# Runs INSIDE the isolation boundary created by DockerExecutor. Contains only
# the benchmark runtime closure: container_entry, adapters, prompt resolver,
# and the provider clients (packages/llm). Deliberately EXCLUDED: database
# drivers, docker SDK, FastAPI, billing code, and any secrets.
#
# Verified runtime deps of that closure (import analysis 2026-08-21): httpx, pydantic.
# Base pinned by digest (M-8); deps pinned to uv.lock versions.
FROM python:3.11-slim@sha256:9c900dea9e8fb7e16277c179b555cc72d29a352dbc33cff48ad5a0412fd5bfc7

# Pin pip behavior and install only the two verified third-party deps.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir httpx==0.28.1 pydantic==2.13.4

# Non-root sandbox user (matches executor's no-root security posture).
RUN addgroup --system --gid 10001 sandbox \
    && adduser --system --uid 10001 --ingroup sandbox --home /sandbox sandbox

WORKDIR /sandbox

# Copy ONLY the benchmark runtime closure. Namespace dirs (packages/, apps/)
# intentionally have no __init__.py at those levels; /app on PYTHONPATH makes
# them importable as namespace packages.
COPY packages/execution_engine/__init__.py        /app/packages/execution_engine/__init__.py
COPY packages/execution_engine/container_entry.py /app/packages/execution_engine/container_entry.py
COPY packages/llm/                                /app/packages/llm/
COPY apps/backend/adapters/                       /app/apps/backend/adapters/
COPY apps/backend/worker/prompt_resolver.py       /app/apps/backend/worker/prompt_resolver.py

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER sandbox

CMD ["python", "-m", "packages.execution_engine.container_entry"]
