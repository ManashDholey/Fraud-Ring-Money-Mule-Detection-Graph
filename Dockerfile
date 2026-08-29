# Multi-stage build: React frontend + FastAPI backend in single container
# Stage 1: Build React frontend
FROM node:18-alpine as client-builder

WORKDIR /build/client

# Copy client files
COPY client/package*.json ./

# Install dependencies (use npm install since we may not have package-lock.json)
# For production builds with reproducible versions, commit package-lock.json and use: npm ci
RUN npm install

# Copy source and build
COPY client/ .
RUN npm run build

# Stage 2: Build Python backend with frontend static files
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt .

# Install Python dependencies to site-packages (accessible to all users)
RUN pip install --no-cache-dir -t /usr/local/lib/python3.11/site-packages -r requirements.txt

# Copy backend application code
COPY backend/ .

# Copy built frontend from client-builder stage into backend/static directory
# FastAPI will serve these static files
COPY --from=client-builder /build/client/dist ./static

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Expose port (Railway will set PORT at runtime)
EXPOSE ${PORT:-8000}

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Start application using shell form so $PORT is expanded
CMD python -m uvicorn main:app --host 0.0.0.0 --port $PORT
