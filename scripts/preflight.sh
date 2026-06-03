#!/usr/bin/env bash
# Pre-flight checks before running the experiment stack.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ERR=0

warn() { echo "[WARN] $*"; }
fail() { echo "[ERROR] $*"; ERR=1; }
ok() { echo "[OK]   $*"; }

echo "=== VR Phobia — preflight / 起動前チェック ==="
echo "Project: $ROOT"
echo

# Node
if ! command -v node >/dev/null 2>&1; then
  fail "Node.js not found. Install from https://nodejs.org or: brew install node"
else
  ok "Node $(node -v)"
fi

if [ ! -d "node_modules" ]; then
  warn "node_modules missing — run: npm install"
  ERR=1
else
  ok "npm dependencies (root)"
fi

if [ ! -d "monitor-electron/node_modules" ]; then
  warn "monitor-electron/node_modules missing — run: npm install"
  ERR=1
else
  ok "monitor-electron dependencies"
fi

# Python venv
if [ ! -x ".venv/bin/python3" ]; then
  warn "No .venv — run: npm run setup:python"
  ERR=1
else
  if .venv/bin/python3 -c "import websockets" 2>/dev/null; then
    ok "Python venv + websockets"
  else
    fail "Python venv missing websockets — run: npm run setup:python"
  fi
  if .venv/bin/python3 -c "import pylsl" 2>/dev/null; then
    ok "pylsl (real EEG / AURA)"
  else
    warn "pylsl not installed — OK for mock; required for npm run experiment (AURA)"
  fi
fi

# TLS
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
  warn "cert.pem/key.pem missing — run: npm run cert"
  ERR=1
else
  ok "TLS cert.pem / key.pem"
fi

# Videos
VIDEO_COUNT=$(find app/assets/videos -maxdepth 1 -name '*.mp4' 2>/dev/null | wc -l | tr -d ' ')
if [ "${VIDEO_COUNT:-0}" -lt 1 ]; then
  fail "No .mp4 files in app/assets/videos/ — copy 360° videos before delivery"
else
  ok "Videos: $VIDEO_COUNT .mp4 files in app/assets/videos/"
fi

# content.json
if [ ! -f "app/data/content.json" ]; then
  fail "Missing app/data/content.json"
else
  ok "content.json"
fi

echo
if [ "$ERR" -ne 0 ]; then
  echo "Preflight FAILED. Fix the items above before running the experiment."
  exit 1
fi
echo "Preflight OK — ready to run npm run experiment or experiment:mock"
exit 0
