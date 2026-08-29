#!/bin/bash
# Frontend startup script for Railway.app
# Railway will execute this script from the repository root

set -e  # Exit on error

echo "🚀 Starting Fraud Detection Frontend..."

# Navigate to client directory
cd client

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm ci
fi

# Build the application
if [ ! -d "dist" ]; then
    echo "🔨 Building React application..."
    npm run build
fi

# Serve the built application
echo "🔥 Starting web server on port ${PORT:-3000}..."
exec npx serve -s dist -l ${PORT:-3000}
