#!/bin/bash
# Startup script for cost-copilot
# Can run either A2A server or ADK web interface based on MODE env variable

set -e

MODE=${MODE:-"a2a"}
PORT=${PORT:-8080}
HOST=${HOST:-0.0.0.0}

if [ "$MODE" = "web" ]; then
    echo "🌐 Starting Cost Copilot Web Interface on http://${HOST}:${PORT}"
    exec adk web src/agents --port ${PORT} --host ${HOST} --no-reload
else
    echo "🤝 Starting Cost Copilot A2A Server on http://${HOST}:${PORT}"
    exec python start_a2a.py
fi
