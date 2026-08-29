#!/bin/bash
# Backend startup script for Railway.app
# Railway will execute this script from the repository root

set -e  # Exit on error

echo "🚀 Starting Fraud Detection Backend..."

# Navigate to backend directory
cd backend

# Install Python dependencies (if not already in Docker build)
if [ ! -d "venv" ]; then
    echo "📦 Installing dependencies..."
    pip install --no-cache-dir -r requirements.txt
fi

# Run the application
echo "🔥 Starting FastAPI server on port ${PORT:-8000}..."
exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
