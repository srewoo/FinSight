#!/usr/bin/env bash
# test.sh — Run all FinSight backend tests
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"

echo "╔══════════════════════════════════════════════╗"
echo "║     FinSight — Running All Tests         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd "$BACKEND"

# Activate venv
if [ -d ".venv" ]; then
  source .venv/bin/activate
else
  echo "  ⚠  No .venv found. Creating one..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -q -r requirements.txt
fi

# Also need pytest-asyncio for LLM client tests
pip install -q pytest pytest-asyncio

# Export the backend URL for integration tests (default: localhost)
export EXPO_PUBLIC_BACKEND_URL="${EXPO_PUBLIC_BACKEND_URL:-http://localhost:8001}"
echo "  Backend URL: $EXPO_PUBLIC_BACKEND_URL"
echo ""

# ── Suite 1: Pure unit tests (no backend needed) ─────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Suite 1: Unit Tests (no network required)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python -m pytest tests/test_technicals.py tests/test_llm_client.py \
  -v --tb=short --no-header \
  -p asyncio_mode=auto \
  --asyncio-mode=auto \
  2>&1

echo ""

# ── Suite 2: Integration tests (backend must be running) ─────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Suite 2: Integration Tests (requires backend)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if backend is reachable
if ! curl -sf "$EXPO_PUBLIC_BACKEND_URL/api/" > /dev/null 2>&1; then
  echo "  ⚠  Backend not reachable at $EXPO_PUBLIC_BACKEND_URL"
  echo "     Run ./start.sh first, then re-run ./test.sh"
  echo "     Skipping integration tests."
  echo ""
  exit 0
fi

python -m pytest \
  tests/test_backend_apis.py \
  tests/test_settings.py \
  tests/test_new_features.py \
  -v --tb=short --no-header \
  -k "not TestAIAnalysis" \
  2>&1

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     All tests complete!                      ║"
echo "╚══════════════════════════════════════════════╝"
