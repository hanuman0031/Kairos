# =============================================================================
# Kairos Backend Dockerfile — Multi-stage, Minimal, Secure
# =============================================================================
# Produces a minimal Python 3.12 image with non-root user, health check,
# and uvloop/httptools for high-performance async serving.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python dependencies into an isolated prefix
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy only the requirements file first to maximise Docker layer caching.
COPY backend/requirements.txt .

# Install packages into /install so we can cherry-pick them in the runtime stage.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lean image with only what we need
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# --- Security: create a dedicated non-root user/group ---
RUN groupadd -r kairos && useradd -r -g kairos -d /app -s /sbin/nologin kairos

WORKDIR /app

# Copy pre-built Python packages from the builder stage.
COPY --from=builder /install /usr/local

# Copy application source code.
COPY backend/app ./app

# Lock down file ownership.
RUN chown -R kairos:kairos /app

# Switch to non-root user for all subsequent commands and at runtime.
USER kairos

# --- Health check ---
# Uses httpx (expected in requirements.txt) to probe the /healthz endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/healthz').raise_for_status()"

EXPOSE 8000

# --- Entrypoint ---
# Exec form ensures PID 1 is uvicorn, enabling proper signal handling.
# 4 workers, uvloop event loop, httptools HTTP parser for max throughput.
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools", "--log-level", "warning"]
