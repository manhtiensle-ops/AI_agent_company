#!/usr/bin/env bash
set -e

PROJECT_ROOT="/home/manhtien/workspace/AI_agent_company"
HOLDING_ROOT="$PROJECT_ROOT/ai-holding"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

echo "=== STARTING AI HOLDING PLATFORM ==="

# 1. Start Studio Control Plane (FastAPI + React Dashboard)
if ! pgrep -f "studio_control_plane.backend.app:app" > /dev/null; then
    echo "Starting Studio Control Plane on port 8500..."
    PYTHONPATH="$HOLDING_ROOT" nohup "$VENV_PYTHON" -m uvicorn studio_control_plane.backend.app:app --host 0.0.0.0 --port 8500 > "$HOLDING_ROOT/studio.log" 2>&1 &
    echo "Studio Control Plane running (PID: $!)"
else
    echo "Studio Control Plane is already running."
fi

# 2. Start Dispatcher Daemon (Actor Loop)
if ! pgrep -f "shared_core.dispatcher_daemon" > /dev/null; then
    echo "Starting Dispatcher Daemon..."
    PYTHONPATH="$HOLDING_ROOT" nohup "$VENV_PYTHON" -m shared_core.dispatcher_daemon > "$HOLDING_ROOT/dispatcher.log" 2>&1 &
    echo "Dispatcher Daemon running (PID: $!)"
else
    echo "Dispatcher Daemon is already running."
fi

echo "=== PLATFORM READY ==="
echo "Studio Dashboard: http://localhost:8500 (LAN: http://192.168.0.117:8500)"
