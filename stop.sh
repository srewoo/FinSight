#!/usr/bin/env bash
# stop.sh — Stop FinSight backend + frontend
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/.logs"

echo "╔══════════════════════════════════════╗"
echo "║     FinSight — Shutting Down     ║"
echo "╚══════════════════════════════════════╝"
echo ""

stop_pid_file() {
  local label="$1"
  local pidfile="$2"
  local port="$3"

  if [ -f "$pidfile" ]; then
    PID=$(cat "$pidfile")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID" && echo "  ✓ Stopped $label (PID $PID)"
    else
      echo "  ℹ  $label PID $PID not running"
    fi
    rm -f "$pidfile"
  else
    echo "  ℹ  No PID file for $label — trying port $port..."
  fi

  # Also kill any process still holding the port
  lsof -ti :"$port" | xargs kill -9 2>/dev/null && echo "  ✓ Cleared port $port" || true
}

stop_pid_file "Backend"  "$LOG_DIR/backend.pid"  8001
stop_pid_file "Frontend" "$LOG_DIR/frontend.pid" 8082

# ── Clear logs ──────────────────────────────────────────────────────────────
rm -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"

# ── Clear all project caches ─────────────────────────────────────────────────
FRONTEND="$ROOT/frontend"
BACKEND="$ROOT/backend"

# Metro bundler cache
rm -rf "$FRONTEND/.metro-cache" \
        "$FRONTEND/node_modules/.cache"

# Expo dev cache
rm -rf "$FRONTEND/.expo"

# Python bytecode cache (backend)
find "$BACKEND" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$BACKEND" -name '*.pyc' -delete 2>/dev/null || true

echo "  ✓ Caches cleared (Metro, Expo, Python __pycache__)"

echo ""
echo "  All services stopped."
