# Multi-stage build for Fraud Detection API Backend
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies to a shared location
COPY requirements.txt .
RUN pip install --no-cache-dir -t /build/lib -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /backend

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder to Python site-packages
COPY --from=builder /build/lib /usr/local/lib/python3.11/site-packages

# Set Python path and environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Copy application code
COPY . .

# Create non-root user for security (appuser can now access system site-packages)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /backend
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Expose port (Railway will override this at runtime)
EXPOSE ${PORT}

# Start application - listen on dynamic PORT environment variable (required for Railway.app)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
