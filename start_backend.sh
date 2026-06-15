#!/bin/bash
# Startup script for GraphMind backend with detailed logging

echo "=========================================="
echo "🚀 Starting GraphMind Backend"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  LOG_LEVEL: DEBUG"
echo "  POSTGRES_ECHO: true"
echo "  Environment: development"
echo ""
echo "Starting uvicorn with detailed output..."
echo "=========================================="
echo ""

# Use the virtual environment uvicorn if it exists, otherwise fallback to global
if [ -f "venv/bin/uvicorn" ]; then
    UVICORN_CMD="venv/bin/uvicorn"
else
    UVICORN_CMD="uvicorn"
fi

$UVICORN_CMD app.main:app --host 0.0.0.0 --port 4915 --log-level debug
