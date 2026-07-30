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
RUN pip install --no-cache-dir uv

# Copy project specification files to cache dependencies
COPY pyproject.toml uv.lock ./

# Sync dependencies (excluding the app itself to maximize layer caching)
# This creates /app/.venv by default
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

# Copy uv from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copy the virtual environment from the builder
COPY --from=builder /app/.venv /opt/venv

# Setup virtual environment variables
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source code
COPY . /app/

# Install the application package using uv to link local modules
RUN uv pip install --no-cache-dir .

# Change ownership to non-root
RUN chown -R atlas:atlas /app

# Switch to non-root user
USER atlas

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Add packages/database to PYTHONPATH so it can be found at runtime since we mount .:/app
ENV PYTHONPATH=/app:/app/packages/database:/app/packages:/app/services

# Default command (can be overridden by compose)
CMD ["uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
