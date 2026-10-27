#!/usr/bin/env bash

echo "=== STOPPING AI HOLDING PLATFORM ==="
pkill -f "studio_control_plane.backend.app:app" || true
pkill -f "shared_core.dispatcher_daemon" || true
echo "All AI Holding platform processes stopped."
