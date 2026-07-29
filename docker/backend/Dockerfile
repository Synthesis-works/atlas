# syntax=docker/dockerfile:1
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies required for psycopg2 and others
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy project specification files first to cache dependencies
COPY pyproject.toml requirements.txt README.md ./

# We will install dependencies into the system site-packages of the builder,
# or we can build wheels. Building wheels is cleaner.
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt || true
# Install all dependencies required by pyproject.toml
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels .


# Final runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime library for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN addgroup --system atlas && adduser --system --group atlas

# Copy built wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copy application source code
COPY . /app/

# Install the application package
RUN pip install --no-cache-dir .

# Change ownership
RUN chown -R atlas:atlas /app

# Switch to non-root user
USER atlas

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Default command (can be overridden by compose)
CMD ["uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
