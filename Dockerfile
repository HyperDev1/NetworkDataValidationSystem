# =============================================================================
# Stage 1: Builder
# Install dependencies with build tools (needed for C extensions like
# pandas, pyarrow, aiohttp). Only runtime artifacts are copied to Stage 2.
# =============================================================================
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies needed for C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install to /install prefix so we can COPY just the packages to the runtime stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# =============================================================================
# Stage 2: Runtime
# Lean production image — no build tools, non-root user, no sensitive files.
# =============================================================================
FROM python:3.13-slim

# Create non-root user for security (CONT-02)
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy only runtime dependencies from the builder stage
COPY --from=builder /install /usr/local

# Copy application code (no config.yaml, no credentials/ — those are volume-mounted)
COPY main.py server.py service.py ./
COPY src/ ./src/

# Set ownership of app directory to non-root user
RUN chown -R appuser:appuser /app

USER appuser

# Cloud Run convention: PORT env var (default 8080)
ENV PORT=8080

EXPOSE 8080

# Docker-level health check (useful for local testing; Cloud Run uses its own HTTP probe)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Entry point: Flask HTTP server
CMD ["python", "server.py"]
