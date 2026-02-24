#!/usr/bin/env bash
# start.sh — Start FinSight backend + frontend
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

echo "╔══════════════════════════════════════╗"
echo "║     FinSight — Starting Up       ║"
echo "╚══════════════════════════════════════╝"

# ── MongoDB ───────────────────────────────────
echo ""
echo "▶ Checking MongoDB..."
if ! mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
  echo "  MongoDB not running — starting it..."
  MONGO_DATA="/tmp/finsight-mongodb-data"
  MONGO_LOG="/tmp/finsight-mongodb.log"
  mkdir -p "$MONGO_DATA"
  if mongod --dbpath "$MONGO_DATA" --logpath "$MONGO_LOG" --port 27017 --fork > /dev/null 2>&1; then
    echo "  ✓ MongoDB started (data: $MONGO_DATA)"
  else
    echo "  ⚠  Could not start MongoDB automatically."
    echo "     Please start MongoDB manually: mongod --dbpath /tmp/finsight-mongodb-data"
  fi
else
  echo "  ✓ MongoDB already running"
fi

# ── Backend ──────────────────────────────────
echo ""
echo "▶ Starting backend (FastAPI on port 8001)..."

if [ ! -f "$BACKEND/.env" ]; then
  echo "  ⚠  $BACKEND/.env not found — backend may fail without MONGO_URL / DB_NAME"
fi

cd "$BACKEND"

# Create or repair venv if needed
VENV_PYTHON=".venv/bin/python3"
if [ ! -d ".venv" ] || [ ! -f "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c "import sys; sys.exit(0)" 2>/dev/null; then
  echo "  Creating/repairing Python virtual environment..."
  rm -rf .venv
  python3 -m venv .venv
fi

source .venv/bin/activate
.venv/bin/pip install -q -r requirements.txt

# Kill any process on port 8001
lsof -ti :8001 | xargs kill -9 2>/dev/null || true

nohup .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --reload \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "  ✓ Backend started (PID $BACKEND_PID) → log: .logs/backend.log"
echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"

# Wait for backend to be ready
echo "  Waiting for backend to be ready..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8001/api/ > /dev/null 2>&1; then
    echo "  ✓ Backend is ready at http://localhost:8001"
    break
  fi
  sleep 1
done

# ── Frontend ─────────────────────────────────
echo ""
echo "▶ Starting frontend (Expo on port 8082)..."

cd "$FRONTEND"

if [ ! -d "node_modules" ]; then
  echo "  Installing node modules..."
  # Clear corrupt ngrok cache entry if it exists
  yarn cache clean @expo/ngrok-bin-darwin-x64 2>/dev/null || true
  yarn install --frozen-lockfile --ignore-engines --ignore-optional
fi


nohup yarn start --port 8082 \
  > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "  ✓ Frontend started (PID $FRONTEND_PID) → log: .logs/frontend.log"
echo "$FRONTEND_PID" > "$LOG_DIR/frontend.pid"

# ── Done ─────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║           All services up!           ║"
echo "╠══════════════════════════════════════╣"
echo "║  Backend API:  http://localhost:8001 ║"
echo "║  Expo Dev:     http://localhost:8082 ║"
echo "║  Logs:         .logs/               ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Run ./stop.sh to stop all services."
