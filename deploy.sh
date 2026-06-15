#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Starting GraphMind Auto-Deployment"
echo "=========================================="

cd /home/GRAG/backend

echo "Fetching latest changes..."
git fetch origin backdev
git reset --hard origin/backdev

echo "Activating virtual environment..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "Installing requirements..."
pip install --upgrade pip
pip install --default-timeout=1000 --retries 10 -r requirements.txt

echo "Applying database migrations..."
alembic upgrade head

echo "Restarting application under PM2..."
pm2 reload all || pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 4915" --name "graphmind-backend"

echo "=========================================="
echo "✅ Auto-Deployment Completed Successfully!"
echo "=========================================="
