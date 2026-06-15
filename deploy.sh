#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Starting GraphMind Auto-Deployment"
echo "=========================================="

cd /home/GRAG/backend

echo "Fetching latest changes..."
git fetch origin backdev
git reset --hard origin/backdev


echo "Restarting application under PM2..."
pm2 reload all || pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 4915" --name "graphmind-backend"

echo "=========================================="
echo "✅ Auto-Deployment Completed Successfully!"
echo "=========================================="

echo "Recent PM2 Logs:"
pm2 logs graphmind-backend --lines 20 --nostream
