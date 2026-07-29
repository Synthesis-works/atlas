# syntax=docker/dockerfile:1
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv to respect uv.lock for deterministic builds
COPY --from=ghcr.io/astral-sh/uv:0.1 /uv /uvx /bin/

# Copy project specification files to cache dependencies
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./

# Install dependencies into a virtual environment
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Sync dependencies (excluding the app itself to maximize layer caching)
RUN uv pip install -r requirements.txt || true
RUN uv sync --no-install-project --no-dev

# Final runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime library for psycopg2 and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry for developer convenience
RUN pip install --no-cache-dir poetry

# Create a non-root user
RUN addgroup --system atlas && adduser --system --group atlas

# Copy the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY . /app/

# Setup virtual environment variables
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install the application package using pip to link local modules
RUN pip install --no-cache-dir .

# Change ownership to non-root
RUN chown -R atlas:atlas /app

# Switch to non-root user
USER atlas

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Default command (can be overridden by compose)
CMD ["uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
