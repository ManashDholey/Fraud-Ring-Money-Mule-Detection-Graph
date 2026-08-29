# Multi-stage build for React + Vite Frontend
# Stage 1: Builder
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Runtime (serve built files)
FROM node:18-alpine

WORKDIR /app

# Install lightweight web server
RUN npm install -g serve

# Copy built application from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# Create non-root user for security
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set default port for Railway.app (can be overridden at runtime)
ENV PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:${PORT}/ || exit 1

# Expose port (Railway will override this at runtime)
EXPOSE ${PORT}

# Start application - listen on dynamic PORT environment variable (required for Railway.app)
CMD sh -c 'serve -s dist -l ${PORT}'
