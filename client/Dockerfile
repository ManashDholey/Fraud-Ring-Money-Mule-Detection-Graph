# Multi-stage build for React + Vite Frontend
# Stage 1: Builder
FROM node:18-alpine AS builder

WORKDIR /client

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
COPY --from=builder /client/dist ./dist
COPY --from=builder /client/package.json ./

# Reuse existing non-root 'node' user from node:18-alpine base image
# (node user already has uid 1000, no need to create a new user)
RUN chown -R node:node /app
USER node

# Set default port for Railway.app (can be overridden at runtime)
ENV PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:${PORT}/ || exit 1

# Expose port (Railway will override this at runtime)
EXPOSE ${PORT}

# Start application - bind to all interfaces (0.0.0.0) for external accessibility
# -l tcp://0.0.0.0:${PORT} ensures container is reachable from host and external traffic
CMD ["sh", "-c", "serve -s dist -l tcp://0.0.0.0:${PORT}"]
