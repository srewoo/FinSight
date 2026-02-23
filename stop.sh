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

echo ""
echo "  All services stopped."
